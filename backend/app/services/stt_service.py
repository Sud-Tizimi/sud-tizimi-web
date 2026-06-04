"""STT provider abstraction.

Defines the contract every provider must satisfy. CP1 ships:
  - MockSTTProvider: deterministic 12-utterance script (same as frontend mockStt.ts)
  - OpenRouterSTTProvider: wraps MockSTTProvider + post-processes FinalEvent
  - FutureLocalSTTProvider: explicit CP2 stub

The abstraction lets CP2 swap in a local Whisper/pyannote pipeline WITHOUT
touching the WebSocket or dispatcher code.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import AsyncIterator, TYPE_CHECKING

from ..config import Settings
from ..core.ws_protocol import SpeakerSeed

if TYPE_CHECKING:
    from .openrouter_service import OpenRouterService

log = logging.getLogger("stt")


# ----------------------- Normalized events -----------------------


class SttEvent:
    """Base marker class for events a provider yields."""


class PartialEvent(SttEvent):
    def __init__(self, speaker_id: str, text: str, progress: float, at_ms: int) -> None:
        self.speaker_id = speaker_id
        self.text = text
        self.progress = progress
        self.at_ms = at_ms


class FinalEvent(SttEvent):
    def __init__(self, speaker_id: str, text: str, at_ms: int) -> None:
        self.speaker_id = speaker_id
        self.text = text
        self.at_ms = at_ms


class AudioLevelEvent(SttEvent):
    def __init__(self, level: int, at_ms: int) -> None:
        self.level = level
        self.at_ms = at_ms


class SpeakerSpeakingEvent(SttEvent):
    def __init__(self, speaker_id: str, speaking: bool) -> None:
        self.speaker_id = speaker_id
        self.speaking = speaking


# ----------------------- Abstract base -----------------------


class BaseSTTProvider(ABC):
    """Every provider must implement these three methods."""

    @abstractmethod
    async def register_speakers(
        self, session_id: str, speakers: list[SpeakerSeed]
    ) -> None: ...

    @abstractmethod
    def stream(self, session_id: str) -> AsyncIterator[SttEvent]: ...

    @abstractmethod
    async def stop(self, session_id: str) -> None: ...

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)


# ----------------------- Mock provider -----------------------


# Same 12-utterance script as frontend/src/lib/mockStt.ts. Tuples:
# (speaker_id, text, start_offset_ms_within_cycle)
MOCK_SCRIPT: list[tuple[str, str, int]] = [
    ("sp-00", "Суд начинается. Прошу всех встать.", 500),
    ("sp-00", "Заседание продолжается. Слушаем истца.", 4200),
    ("sp-01", "Уважаемый суд, позвольте изложить обстоятельства дела.", 7800),
    (
        "sp-01",
        "По нашему мнению, решение администрации было принято с нарушением процедуры.",
        13200,
    ),
    ("sp-00", "Спасибо. Слово предоставляется ответчику.", 19200),
    ("sp-02", "Ваша честь, мы не согласны с позицией истца.", 22200),
    (
        "sp-02",
        "Все процедуры были соблюдены в полном объёме, согласно действующему законодательству.",
        26200,
    ),
    ("sp-03", "Ваша честь, разрешите дополнить позицию стороны истца.", 32200),
    ("sp-00", "Спасибо.", 35200),
    (
        "sp-03",
        "Согласно статье 117 Гражданского кодекса, наш клиент имеет безусловное право на компенсацию.",
        37200,
    ),
    ("sp-00", "Суд удаляется на совещание. Прошу всех оставаться на местах.", 45000),
    ("sp-01", "Благодарю, Ваша честь.", 49200),
]

PARTIAL_INTERVAL_MS = 450
FINAL_DELAY_MS = 1800
AUDIO_INTERVAL_MS = 200


def _truncate(text: str, ratio: float) -> str:
    cut = max(1, int(len(text) * ratio))
    if cut >= len(text):
        return text
    return text[:cut].rstrip() + "…"


class MockSTTProvider(BaseSTTProvider):
    """Reproduces the same SCRIPT as the frontend mock for CP1 demo.

    The provider owns its audio-level queue so a future real provider can
    implement it differently (e.g. VU-meter on a real mic stream).
    """

    def __init__(self, loop_sec: int = 52) -> None:
        self.loop_ms = loop_sec * 1000
        self._stops: dict[str, asyncio.Event] = {}
        # Audio-level events are produced by a parallel task and drained
        # by the stream_dispatcher via this queue.
        self._audio_queue: asyncio.Queue[AudioLevelEvent] = asyncio.Queue()

    # ----- public API -----

    async def register_speakers(
        self, session_id: str, speakers: list[SpeakerSeed]
    ) -> None:
        self._stops.setdefault(session_id, asyncio.Event())

    async def stop(self, session_id: str) -> None:
        ev = self._stops.get(session_id)
        if ev is not None:
            ev.set()

    async def stream(self, session_id: str) -> AsyncIterator[SttEvent]:
        ev = self._stops.setdefault(session_id, asyncio.Event())
        loop_start = self.now_ms()
        audio_task = asyncio.create_task(
            self._audio_pump(ev, loop_start),
            name=f"audio-pump-{session_id}",
        )
        try:
            while not ev.is_set():
                for spk, text, start_ms in MOCK_SCRIPT:
                    if ev.is_set():
                        return
                    await self._sleep_until(loop_start, start_ms, ev)
                    if ev.is_set():
                        return
                    now = self.now_ms() - loop_start
                    yield SpeakerSpeakingEvent(spk, True)
                    yield PartialEvent(spk, _truncate(text, 0.40), 0.40, now)
                    await self._interruptible_sleep(PARTIAL_INTERVAL_MS / 1000, ev)
                    if ev.is_set():
                        return
                    now = self.now_ms() - loop_start
                    yield PartialEvent(spk, _truncate(text, 0.75), 0.75, now)
                    remaining = max(0, (FINAL_DELAY_MS - PARTIAL_INTERVAL_MS) / 1000)
                    await self._interruptible_sleep(remaining, ev)
                    if ev.is_set():
                        return
                    now = self.now_ms() - loop_start
                    yield PartialEvent(spk, text, 1.0, now)
                    yield FinalEvent(spk, text, now)
                    yield SpeakerSpeakingEvent(spk, False)
                # Re-anchor at the top of each cycle so we don't drift.
                loop_start = self.now_ms()
        finally:
            audio_task.cancel()

    # ----- internals -----

    async def _audio_pump(
        self, ev: asyncio.Event, loop_start: int
    ) -> None:
        try:
            while not ev.is_set():
                await asyncio.sleep(AUDIO_INTERVAL_MS / 1000)
                if ev.is_set():
                    return
                level = int(30 + random.random() * 50)  # 30..80
                try:
                    self._audio_queue.put_nowait(
                        AudioLevelEvent(level, self.now_ms() - loop_start)
                    )
                except asyncio.QueueFull:
                    pass
        except asyncio.CancelledError:
            return

    async def _sleep_until(
        self, anchor_ms: int, target_offset_ms: int, ev: asyncio.Event
    ) -> None:
        target = anchor_ms + target_offset_ms
        while True:
            now = self.now_ms()
            if now >= target:
                return
            remaining_s = (target - now) / 1000
            try:
                await asyncio.wait_for(ev.wait(), timeout=min(remaining_s, 0.25))
                return  # stopped
            except asyncio.TimeoutError:
                continue

    async def _interruptible_sleep(self, seconds: float, ev: asyncio.Event) -> None:
        try:
            await asyncio.wait_for(ev.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return
        # if ev was set, just return — outer loop checks ev.is_set()


# ----------------------- OpenRouter wrapper provider -----------------------


class OpenRouterSTTProvider(BaseSTTProvider):
    """Wraps another provider (typically MockSTTProvider) and post-processes
    FinalEvent text via the OpenRouter service. Failure of OpenRouter must
    not break the stream — falls back to the original text.
    """

    def __init__(
        self, inner: BaseSTTProvider, openrouter: "OpenRouterService"
    ) -> None:
        self._inner = inner
        self._or = openrouter

    async def register_speakers(
        self, session_id: str, speakers: list[SpeakerSeed]
    ) -> None:
        await self._inner.register_speakers(session_id, speakers)

    async def stop(self, session_id: str) -> None:
        await self._inner.stop(session_id)

    async def stream(self, session_id: str) -> AsyncIterator[SttEvent]:
        async for ev in self._inner.stream(session_id):
            if isinstance(ev, FinalEvent):
                normalized = await self._or.normalize(ev.text)
                if normalized and normalized != ev.text:
                    ev.text = normalized
            yield ev


# ----------------------- CP2 stub -----------------------


class FutureLocalSTTProvider(BaseSTTProvider):
    """Placeholder for CP2 — will wrap a local Whisper/pyannote pipeline."""

    async def register_speakers(
        self, session_id: str, speakers: list[SpeakerSeed]
    ) -> None:
        raise NotImplementedError("CP2: FutureLocalSTTProvider not implemented yet")

    async def stop(self, session_id: str) -> None:
        raise NotImplementedError("CP2: FutureLocalSTTProvider not implemented yet")

    async def stream(self, session_id: str) -> AsyncIterator[SttEvent]:
        raise NotImplementedError("CP2: FutureLocalSTTProvider not implemented yet")
        if False:  # pragma: no cover — make this an async generator
            yield  # type: ignore[unreachable]


# ----------------------- Factory -----------------------


def build_stt_provider(settings: Settings) -> BaseSTTProvider:
    name = settings.stt_provider
    if name == "mock":
        return MockSTTProvider(loop_sec=settings.script_loop_sec)
    if name == "openrouter":
        # Local import to avoid httpx being loaded when not needed
        from .openrouter_service import OpenRouterService

        mock = MockSTTProvider(loop_sec=settings.script_loop_sec)
        ors = OpenRouterService(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            timeout_s=settings.openrouter_timeout_s,
        )
        return OpenRouterSTTProvider(inner=mock, openrouter=ors)
    if name == "future_local":
        return FutureLocalSTTProvider()
    raise ValueError(f"unknown_stt_provider:{name}")
