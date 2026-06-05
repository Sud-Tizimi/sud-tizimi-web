"""In-memory session registry + broadcast helper.

No DB, no Redis, no Kafka — CP1 lives entirely in process memory.
A process restart wipes everything; that is acceptable for the demo.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from ..config import Settings
from ..core.errors import SessionNotFound
from ..core.ids import gen_session_id
from ..core.ws_protocol import (
    ServerAudioLevel,
    ServerMessage,
    ServerSpeakerRegistered,
    SpeakerSeed,
    make_session_ready,
)
from .stream_dispatcher import StreamDispatcher  # noqa: F401  (type-only via TYPE_CHECKING)

if TYPE_CHECKING:
    from .stt_service import BaseSTTProvider
    from .stream_dispatcher import StreamDispatcher

log = logging.getLogger("session_manager")


@dataclass
class Session:
    id: str
    case: dict[str, Any]
    started_at: datetime
    speakers: dict[str, SpeakerSeed] = field(default_factory=dict)
    partial_index: dict[str, str] = field(default_factory=dict)  # speakerId -> entryId
    transcript: list[dict[str, Any]] = field(default_factory=list)
    final_count: int = 0
    stopped: bool = False
    sockets: set[Any] = field(default_factory=set)  # set[WebSocket]
    stream_tasks: list[asyncio.Task] = field(default_factory=list)
    audio_level_enabled: bool = True
    # Pending new speakers to announce on next stream start
    _pending_speakers: list[SpeakerSeed] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case": self.case,
            "startedAt": self.started_at.isoformat(),
            "stopped": self.stopped,
            "finalCount": self.final_count,
            "speakers": [s.model_dump() for s in self.speakers.values()],
        }


class SessionManager:
    """Owns the in-memory registry of sessions and broadcasts WS events to them."""

    def __init__(
        self,
        provider: "BaseSTTProvider",
        dispatcher: StreamDispatcher,
        settings: Settings,
    ) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self.provider = provider
        self.dispatcher = dispatcher
        self.settings = settings

    # ----------------------- Lifecycle -----------------------

    async def create_session(
        self,
        case_info: dict[str, Any],
        speakers: list[SpeakerSeed],
    ) -> Session:
        sid = gen_session_id()
        async with self._lock:
            sess = Session(
                id=sid,
                case=case_info,
                started_at=datetime.now(timezone.utc),
                speakers={},
            )
            for seed in speakers:
                generic = self._generic_speaker_seed(seed.id, sess)
                sess.speakers[generic.id] = generic
            self._sessions[sid] = sess

        # Register speakers with the provider so the script knows who is who.
        try:
            await self.provider.register_speakers(sid, list(sess.speakers.values()))
        except Exception:  # provider in a bad state shouldn't block session creation
            log.exception("provider_register_speakers_failed sid=%s", sid)

        # Kick off streaming so the WS gets events even before the first client connects.
        await self.start_streaming(sid)
        return sess

    async def start_streaming(self, sid: str) -> None:
        sess = await self._get_or_404(sid)
        if sess.stream_tasks or sess.stopped:
            return
        task = asyncio.create_task(
            self.dispatcher.run(sess, self),
            name=f"dispatcher-{sid}",
        )
        sess.stream_tasks.append(task)

    async def stop_session(self, sid: str) -> dict[str, Any]:
        sess = await self._get_or_404(sid)
        sess.stopped = True
        for task in sess.stream_tasks:
            task.cancel()
        sess.stream_tasks.clear()
        try:
            await self.provider.stop(sid)
        except Exception:
            log.exception("provider_stop_failed sid=%s", sid)

        # Close any attached sockets so the client transitions out of LIVE.
        for ws in list(sess.sockets):
            try:
                await ws.close(code=1000, reason="session_stopped")
            except Exception:
                pass
        sess.sockets.clear()

        duration = int(
            (datetime.now(timezone.utc) - sess.started_at).total_seconds()
        )
        return {
            "sessionId": sid,
            "stoppedAt": datetime.now(timezone.utc).isoformat(),
            "durationSec": duration,
            "finalEntryCount": sess.final_count,
        }

    async def shutdown_all(self) -> None:
        for sess in list(self._sessions.values()):
            for task in sess.stream_tasks:
                task.cancel()
            try:
                await self.provider.stop(sess.id)
            except Exception:
                log.exception("provider_stop_failed_on_shutdown sid=%s", sess.id)
        self._sessions.clear()

    # ----------------------- Socket attach / detach -----------------------

    async def attach_socket(self, sid: str, ws) -> bool:
        sess = self._sessions.get(sid)
        if sess is None or sess.stopped:
            return False
        sess.sockets.add(ws)
        # Resend the current snapshot so a reconnecting client gets speakers
        # even if it missed the initial attach.
        await self._send_safe(
            ws,
            make_session_ready(sid, sess.started_at, list(sess.speakers.values())),
        )
        return True

    async def detach_socket(self, sid: str, ws) -> None:
        sess = self._sessions.get(sid)
        if sess is not None:
            sess.sockets.discard(ws)

    # ----------------------- Broadcast helpers -----------------------

    async def broadcast(self, sid: str, msg: ServerMessage) -> None:
        sess = self._sessions.get(sid)
        if sess is None:
            return
        # Per-session audio_level filter
        if isinstance(msg, ServerAudioLevel) and not sess.audio_level_enabled:
            return
        dead: list[Any] = []
        payload = msg.model_dump()
        for ws in list(sess.sockets):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            sess.sockets.discard(d)

    # ----------------------- Speaker registration -----------------------

    async def register_speakers(self, sid: str, seeds: list[SpeakerSeed]) -> list[SpeakerSeed]:
        sess = await self._get_or_404(sid)
        added: list[SpeakerSeed] = []
        for seed in seeds:
            generic = self._generic_speaker_seed(seed.id, sess)
            existing = sess.speakers.get(generic.id)
            if existing:
                continue
            sess.speakers[generic.id] = generic
            added.append(generic)
        if added:
            try:
                await self.provider.register_speakers(sid, added)
            except Exception:
                log.exception("provider_register_speakers_failed sid=%s", sid)
        return added

    async def ensure_speaker(self, sid: str, speaker_id: str) -> SpeakerSeed:
        sess = await self._get_or_404(sid)
        existing = sess.speakers.get(speaker_id)
        if existing:
            return existing

        seed = self._generic_speaker_seed(speaker_id, sess)
        sess.speakers[seed.id] = seed
        try:
            await self.provider.register_speakers(sid, [seed])
        except Exception:
            log.exception("provider_register_speakers_failed sid=%s", sid)
        await self.broadcast(sid, ServerSpeakerRegistered(speaker=seed))
        return seed

    # ----------------------- Queries -----------------------

    async def _get_or_404(self, sid: str) -> Session:
        sess = self._sessions.get(sid)
        if sess is None:
            raise SessionNotFound(sid)
        return sess

    def get(self, sid: str) -> Optional[Session]:
        return self._sessions.get(sid)

    def list_summaries(self) -> list[dict[str, Any]]:
        return [s.public_dict() for s in self._sessions.values()]

    # ----------------------- Internals -----------------------

    @staticmethod
    async def _send_safe(ws, msg: ServerMessage) -> None:
        try:
            await ws.send_json(msg.model_dump())
        except Exception:
            log.debug("send_failed", exc_info=True)

    @staticmethod
    def _generic_speaker_seed(speaker_id: str, sess: Session) -> SpeakerSeed:
        n = _speaker_number_from_id(speaker_id) or (len(sess.speakers) + 1)
        return SpeakerSeed(
            id=speaker_id,
            label=f"Speaker {n}",
            shortLabel=f"SP{n}",
            role="speaker",
        )


def _speaker_number_from_id(speaker_id: str) -> int | None:
    import re

    match = re.search(r"(?:speaker|spk|sp)[-_ ]?0*(\d+)$", speaker_id, re.IGNORECASE)
    if match is None:
        return None
    n = int(match.group(1))
    return 1 if n == 0 else n
