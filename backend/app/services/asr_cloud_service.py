"""Cloud/local ASR integration imported from voice-asr-cloud-main.

The public service returns one normalized shape regardless of provider:
segments with speaker labels, word timestamps, and confidence. The /sessions
page uses it as the final high-quality pass after microphone recording stops.
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile

from ..api.schemas.asr import ASRSegment, ASRTranscriptionResponse, ASRWord
from ..config import Settings

AUDIO_FORMATS = {
    ".mp3": ("audio/mpeg", "mp3"),
    ".wav": ("audio/wav", "wav"),
    ".ogg": ("audio/ogg", "ogg"),
    ".flac": ("audio/flac", "flac"),
    ".m4a": ("audio/mp4", "m4a"),
    ".mp4": ("audio/mp4", "mp4"),
    ".webm": ("audio/webm", "webm"),
    ".aac": ("audio/aac", "aac"),
}

SYSTEM_PROMPT = """\
You are a professional ASR (Automatic Speech Recognition) and speaker diarization engine.

For the given audio, produce WORD-LEVEL transcription with speaker diarization.

Return ONLY valid JSON matching this exact schema:
{
  "speakers_count": <int>,
  "language": "<detected language>",
  "duration": "<MM:SS>",
  "segments": [
    {
      "id": <int starting at 1>,
      "speaker": "Speaker N",
      "words": [
        {
          "word": "<single token, punctuation attached>",
          "start": "<MM:SS.mmm>",
          "end": "<MM:SS.mmm>",
          "confidence": <float 0.0-1.0>
        }
      ]
    }
  ],
  "full_transcript": "<complete: SPEAKER_N: text per line>"
}

RULES:
- Transcribe VERBATIM in the language actually spoken, using that language's native script.
- NEVER translate or transliterate into another language/script.
- Every spoken word must appear in 'words' with its own start/end timestamp.
- confidence = certainty this word was transcribed correctly.
- Include filler words with timestamps.
- Segment breaks ONLY on speaker changes.
- No summary field.
"""


def _language_directive(language: str | None) -> str:
    if language:
        return (
            "\n\nLANGUAGE LOCK:\n"
            f"- The spoken language is {language}.\n"
            f"- Transcribe ONLY in {language}, in its native/standard script.\n"
            "- NEVER translate. NEVER transliterate into another script.\n"
        )
    return (
        "\n\nLANGUAGE DETECTION:\n"
        "- Infer the language from the audio and transcribe verbatim in that language's script.\n"
        "- Do not default short Uzbek/Latin clips to Russian/Cyrillic.\n"
    )


def _detect_audio(raw: bytes, filename: str) -> tuple[str, str]:
    suffix = Path(filename or "audio.webm").suffix.lower()
    if raw[:4] == b"\x1a\x45\xdf\xa3":
        return "audio/webm", "webm"
    if raw[:4] == b"RIFF":
        return "audio/wav", "wav"
    if raw[:3] == b"ID3" or raw[:2] == b"\xff\xfb":
        return "audio/mpeg", "mp3"
    return AUDIO_FORMATS.get(suffix, ("audio/webm", "webm"))


def _strip_fences(text: str) -> str:
    clean = text.strip()
    for fence in ("```json", "```"):
        if clean.startswith(fence):
            clean = clean[len(fence):]
    if clean.endswith("```"):
        clean = clean[:-3]
    return clean.strip()


def _segment_text(words: list[ASRWord]) -> str:
    return " ".join(w.word for w in words).strip()


def _normalize_response(
    data: dict[str, Any],
    *,
    provider: str,
    model: str,
    elapsed: float,
) -> ASRTranscriptionResponse:
    segments: list[ASRSegment] = []
    for idx, raw_seg in enumerate(data.get("segments") or []):
        words = [
            ASRWord(
                word=str(w.get("word", "")).strip(),
                start=str(w.get("start", "00:00.000")),
                end=str(w.get("end", "00:00.000")),
                confidence=float(w.get("confidence", 1.0) or 1.0),
            )
            for w in raw_seg.get("words", [])
            if str(w.get("word", "")).strip()
        ]
        text = str(raw_seg.get("text") or "").strip() or _segment_text(words)
        if not text and not words:
            continue
        start = str(raw_seg.get("start") or (words[0].start if words else "00:00.000"))
        end = str(raw_seg.get("end") or (words[-1].end if words else start))
        segments.append(
            ASRSegment(
                id=int(raw_seg.get("id") or idx + 1),
                speaker=str(raw_seg.get("speaker") or f"Speaker {idx + 1}"),
                start=start,
                end=end,
                text=text,
                words=words,
            )
        )

    full = str(data.get("full_transcript") or "").strip()
    if not full:
        full = "\n".join(f"{seg.speaker}: {seg.text}" for seg in segments)

    speakers = data.get("speakers_count")
    if not isinstance(speakers, int):
        speakers = len({seg.speaker for seg in segments})

    return ASRTranscriptionResponse(
        provider=provider,
        model=model,
        speakersCount=speakers,
        language=str(data.get("language") or "unknown"),
        duration=str(data.get("duration") or "00:00"),
        fullTranscript=full,
        processingTimeS=round(elapsed, 2),
        segments=segments,
    )


def _normalize_local_response(
    data: dict[str, Any],
    *,
    elapsed: float,
) -> ASRTranscriptionResponse:
    diarized = data.get("diarized_segments")
    if isinstance(diarized, list) and diarized:
        normalized_segments = []
        for idx, seg in enumerate(diarized):
            start = float(seg.get("start", 0) or 0)
            end = float(seg.get("end", start) or start)
            text = str(seg.get("text") or "").strip()
            normalized_segments.append(
                {
                    "id": idx + 1,
                    "speaker": str(seg.get("speaker") or f"Speaker {idx + 1}"),
                    "start": _format_ts(start),
                    "end": _format_ts(end),
                    "text": text,
                    "words": [
                        {
                            "word": token,
                            "start": _format_ts(start),
                            "end": _format_ts(end),
                            "confidence": 1.0,
                        }
                        for token in text.split()
                    ],
                }
            )
        return _normalize_response(
            {
                "segments": normalized_segments,
                "language": data.get("language") or "unknown",
                "duration": _format_duration(data.get("duration")),
                "full_transcript": data.get("text") or "",
            },
            provider="local",
            model=str(data.get("model") or "local-asr"),
            elapsed=elapsed,
        )

    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    normalized_segments = []
    if segments:
        for idx, seg in enumerate(segments):
            start = float(seg.get("start", 0) or 0)
            end = float(seg.get("end", start) or start)
            text = str(seg.get("text") or "").strip()
            normalized_segments.append(
                {
                    "id": idx + 1,
                    "speaker": "Speaker 1",
                    "start": _format_ts(start),
                    "end": _format_ts(end),
                    "text": text,
                    "words": [
                        {
                            "word": token,
                            "start": _format_ts(start),
                            "end": _format_ts(end),
                            "confidence": 1.0,
                        }
                        for token in text.split()
                    ],
                }
            )
    else:
        text = str(data.get("text") or data.get("transcription") or "").strip()
        normalized_segments = [
            {
                "id": 1,
                "speaker": "Speaker 1",
                "text": text,
                "words": [
                    {
                        "word": token,
                        "start": "00:00.000",
                        "end": "00:00.000",
                        "confidence": 1.0,
                    }
                    for token in text.split()
                ],
            }
        ] if text else []

    return _normalize_response(
        {
            "segments": normalized_segments,
            "language": data.get("language") or "unknown",
            "duration": _format_duration(data.get("duration")),
            "full_transcript": data.get("text") or data.get("transcription") or "",
        },
        provider="local",
        model=str(data.get("model") or "local-asr"),
        elapsed=elapsed,
    )


def _format_ts(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = seconds % 60
    return f"{minutes:02d}:{rest:06.3f}"


def _format_duration(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{int(value // 60):02d}:{int(value % 60):02d}"
    if isinstance(value, str) and value:
        return value
    return "00:00"


async def transcribe_audio(
    *,
    settings: Settings,
    audio: UploadFile,
    provider: str | None,
    language: str | None,
    num_speakers: int | None,
    diarize: bool,
) -> ASRTranscriptionResponse:
    selected = (provider or settings.asr_provider).lower().strip()
    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="audio_empty")
    if selected == "local":
        return await _transcribe_local(settings, audio.filename or "audio.webm", raw, language, diarize)
    if selected == "openrouter":
        return await _transcribe_openrouter(settings, audio.filename or "audio.webm", raw, language, num_speakers)
    if selected == "aistudio":
        try:
            return await _transcribe_aistudio(settings, audio.filename or "audio.webm", raw, language, num_speakers)
        except HTTPException as exc:
            # Google AI Studio can occasionally return upstream ServerError for
            # audio requests. Keep the UI alive by falling back to the
            # OpenRouter Gemini route when a key is configured.
            if settings.openrouter_api_key:
                return await _transcribe_openrouter(settings, audio.filename or "audio.webm", raw, language, num_speakers)
            raise exc
    raise HTTPException(status_code=400, detail="unsupported_asr_provider")


async def _transcribe_local(
    settings: Settings,
    filename: str,
    raw: bytes,
    language: str | None,
    diarize: bool,
) -> ASRTranscriptionResponse:
    t0 = time.perf_counter()
    mime, _ = _detect_audio(raw, filename)
    files = {"file": (filename, raw, mime)}
    data = {
        "language": language or "Uzbek",
        "return_timestamps": "true",
        "diarize": "true" if diarize else "false",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.asr_timeout_s) as client:
            resp = await client.post(
                f"{settings.local_asr_base_url.rstrip('/')}/transcribe",
                data=data,
                files=files,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"local_asr_unavailable:{exc.__class__.__name__}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    try:
        payload = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="local_asr_invalid_json")
    return _normalize_local_response(payload, elapsed=time.perf_counter() - t0)


async def local_asr_health(settings: Settings) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{settings.local_asr_base_url.rstrip('/')}/health")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"local_asr_unavailable:{exc.__class__.__name__}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="local_asr_invalid_json")


async def local_asr_languages(settings: Settings) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{settings.local_asr_base_url.rstrip('/')}/languages")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"local_asr_unavailable:{exc.__class__.__name__}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="local_asr_invalid_json")


async def _transcribe_openrouter(
    settings: Settings,
    filename: str,
    raw: bytes,
    language: str | None,
    num_speakers: int | None,
) -> ASRTranscriptionResponse:
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=503, detail="openrouter_api_key_missing")
    t0 = time.perf_counter()
    _, fmt = _detect_audio(raw, filename)
    hints = ["Transcribe with word-level timestamps and speaker diarization."]
    if language:
        hints.append(f"Primary language: {language}.")
    if num_speakers:
        hints.append(f"Hint: exactly {num_speakers} distinct speakers.")
    hints.append("Return ONLY valid JSON.")
    payload = {
        "model": settings.asr_openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + _language_directive(language)},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.standard_b64encode(raw).decode(),
                            "format": fmt,
                        },
                    },
                    {"type": "text", "text": " ".join(hints)},
                ],
            },
        ],
        "response_format": {"type": "json_object"},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.asr_timeout_s) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://sud-tizimi.local",
                    "X-Title": "Sud-Tizimi ASR",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"openrouter_unavailable:{exc.__class__.__name__}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    try:
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(_strip_fences(content))
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="openrouter_invalid_asr_json")
    return _normalize_response(
        data,
        provider="openrouter",
        model=settings.asr_openrouter_model,
        elapsed=time.perf_counter() - t0,
    )


async def _transcribe_aistudio(
    settings: Settings,
    filename: str,
    raw: bytes,
    language: str | None,
    num_speakers: int | None,
) -> ASRTranscriptionResponse:
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="gemini_api_key_missing")
    try:
        from google import genai
        from google.genai import types as gtypes
    except Exception:
        raise HTTPException(status_code=503, detail="google_genai_not_installed")

    mime, _ = _detect_audio(raw, filename)
    hints = ["Transcribe with word-level timestamps and speaker diarization."]
    if language:
        hints.append(f"Primary language: {language}.")
    if num_speakers:
        hints.append(f"Hint: exactly {num_speakers} distinct speakers.")
    hints.append("Return ONLY valid JSON.")
    t0 = time.perf_counter()

    def run() -> str:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.asr_aistudio_model,
            contents=[
                gtypes.Content(
                    role="user",
                    parts=[
                        gtypes.Part.from_bytes(data=raw, mime_type=mime),
                        gtypes.Part(text=" ".join(hints)),
                    ],
                )
            ],
            config=gtypes.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT + _language_directive(language),
                response_mime_type="application/json",
            ),
        )
        return response.text or "{}"

    import asyncio

    try:
        content = await asyncio.to_thread(run)
        data = json.loads(_strip_fences(content))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="aistudio_invalid_asr_json")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"aistudio_unavailable:{exc.__class__.__name__}")
    return _normalize_response(
        data,
        provider="aistudio",
        model=settings.asr_aistudio_model,
        elapsed=time.perf_counter() - t0,
    )
