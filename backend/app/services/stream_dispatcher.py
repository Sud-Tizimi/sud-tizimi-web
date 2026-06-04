"""Bridges provider events into Session state and WebSocket broadcasts.

The dispatcher is the seam between STT providers and the rest of the app.
It owns NO transport details — it just calls `mgr.broadcast(...)` and
mutates `session.transcript / partial_index`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from ..core.ids import gen_entry_id
from ..core.ws_protocol import (
    ServerAudioLevel,
    ServerFinal,
    ServerPartial,
    ServerSpeakerSpeaking,
)
from .stt_service import (
    AudioLevelEvent,
    BaseSTTProvider,
    FinalEvent,
    PartialEvent,
    SpeakerSpeakingEvent,
)

if TYPE_CHECKING:
    from .session_manager import Session, SessionManager

log = logging.getLogger("dispatcher")


class StreamDispatcher:
    async def run(self, session: Session, mgr: SessionManager) -> None:
        provider: BaseSTTProvider = mgr.provider
        audio_queue: Optional[asyncio.Queue] = getattr(provider, "_audio_queue", None)
        audio_task: Optional[asyncio.Task] = None
        if audio_queue is not None:
            audio_task = asyncio.create_task(
                self._pump_audio(session, mgr, audio_queue),
                name=f"audio-pump-{session.id}",
            )
        try:
            async for ev in provider.stream(session.id):
                if isinstance(ev, PartialEvent):
                    await self._handle_partial(session, mgr, ev)
                elif isinstance(ev, FinalEvent):
                    await self._handle_final(session, mgr, ev)
                elif isinstance(ev, SpeakerSpeakingEvent):
                    await mgr.broadcast(
                        session.id,
                        ServerSpeakerSpeaking(
                            speakerId=ev.speaker_id, speaking=ev.speaking
                        ),
                    )
                # AudioLevelEvent comes from the audio_queue, not the main stream.
        except asyncio.CancelledError:
            log.info("dispatcher_cancelled sid=%s", session.id)
        except Exception:
            log.exception("dispatcher_error sid=%s", session.id)
        finally:
            if audio_task is not None:
                audio_task.cancel()
                try:
                    await audio_task
                except (asyncio.CancelledError, Exception):
                    pass

    # ----------------------- handlers -----------------------

    async def _handle_partial(
        self, session: Session, mgr: SessionManager, ev: PartialEvent
    ) -> None:
        entry_id = session.partial_index.get(ev.speaker_id) or gen_entry_id(
            ev.speaker_id, ev.at_ms
        )
        session.partial_index[ev.speaker_id] = entry_id
        await mgr.broadcast(
            session.id,
            ServerPartial(
                entryId=entry_id,
                speakerId=ev.speaker_id,
                text=ev.text,
                atMs=ev.at_ms,
                progress=ev.progress,
            ),
        )

    async def _handle_final(
        self, session: Session, mgr: SessionManager, ev: FinalEvent
    ) -> None:
        entry_id = session.partial_index.pop(
            ev.speaker_id, gen_entry_id(ev.speaker_id, ev.at_ms)
        )
        session.transcript.append(
            {
                "id": entry_id,
                "speakerId": ev.speaker_id,
                "text": ev.text,
                "atMs": ev.at_ms,
                "isFinal": True,
            }
        )
        session.final_count += 1
        await mgr.broadcast(
            session.id,
            ServerFinal(
                entryId=entry_id,
                speakerId=ev.speaker_id,
                text=ev.text,
                rawText=ev.text,  # CP1: provider already mutated .text in place
                atMs=ev.at_ms,
                postProcessed=False,
            ),
        )

    async def _pump_audio(
        self,
        session: Session,
        mgr: SessionManager,
        queue: asyncio.Queue,
    ) -> None:
        try:
            while True:
                ev: AudioLevelEvent = await queue.get()
                await mgr.broadcast(
                    session.id,
                    ServerAudioLevel(level=ev.level, atMs=ev.at_ms),
                )
        except asyncio.CancelledError:
            return
