# Faysal AI Backend (CP1 MVP)

FastAPI backend for the Faysal AI real-time court transcription platform.

## Status

- **CP1 (MVP)**: working end-to-end. Frontend `Sessions` page can switch between
  the in-browser mock and this backend via the `useBackendStt` feature flag.
- **CP2 (planned)**: local STT model, OCR, AI summary, DOCX generation, notifications.

## Stack

- Python 3.12
- FastAPI + Uvicorn
- Pydantic v2 / pydantic-settings
- httpx (async OpenRouter client)
- WebSocket via `uvicorn[standard]`

No database, no Redis, no Kafka. In-memory state only.

## Run

```bash
cd backend
cp .env.example .env       # leave OPENROUTER_API_KEY empty for first run
bash run.sh                # or: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server starts on `http://127.0.0.1:8000`. Swagger UI: `/docs`.

## REST API

| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/health`          | Liveness probe |
| GET  | `/api/health/ready`    | Readiness probe |
| POST | `/api/sessions/start`  | Create a session, returns `sessionId` + `wsUrl` |
| POST | `/api/sessions/{id}/stop` | Stop a session |
| GET  | `/api/sessions`        | List sessions (debug) |
| GET  | `/api/sessions/{id}`   | Session public state (debug) |

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/start \
  -H 'content-type: application/json' \
  -d '{
    "caseNumber": "CASE-2026-0241",
    "title": "Demo",
    "judge": "Hon. R. Karimov",
    "speakers": [
      {"id": "sp-00", "label": "Hon. R. Karimov",    "role": "judge"},
      {"id": "sp-01", "label": "A. Abdullayev",      "role": "plaintiff"},
      {"id": "sp-02", "label": "Tashkent City Admin","role": "defendant"},
      {"id": "sp-03", "label": "L. Tursunov",        "role": "lawyer"}
    ]
  }'
```

## WebSocket API

Endpoint: `ws://{host}/ws/sessions/{sessionId}`

JSON-only in CP1. The server simulates audio/STT internally — clients send
control messages, never binary frames.

### Server → Client

| Type | Fields | When |
|---|---|---|
| `session_ready`         | `sessionId, startedAt, speakers[]`              | Right after accept + on reconnect |
| `speaker_registered`    | `speaker`                                       | Client `register_speakers` adds new entries |
| `partial`               | `entryId, speakerId, text, atMs, progress`      | Every ~450ms during an utterance |
| `final`                 | `entryId, speakerId, text, rawText, atMs, postProcessed` | At 1800ms — commits the partial |
| `audio_level`           | `level (0-100), atMs`                           | Every 200ms while live |
| `speaker_speaking`      | `speakerId, speaking`                           | Utterance start/end |
| `ping`                  | `t`                                             | Server heartbeat every 20s |
| `error`                 | `code, message`                                 | Protocol / internal errors |

### Client → Server

| Type | Fields | Effect |
|---|---|---|
| `register_speakers`     | `speakers[]`  | Pre-seed / add speakers (idempotent) |
| `subscribe_audio_level` | `enabled`     | Mute / unmute `audio_level` events |
| `ping`                  | `t`           | Heartbeat probe — server replies with `pong` |
| `pong`                  | —             | Reply to server `ping` |

### Close codes

| Code | Meaning |
|---|---|
| 1000 | Normal |
| 4000 | Idle timeout (>45s without inbound) |
| 4404 | Session not found |
| 1011 | Server error |

## Architecture

```
app/
├── main.py                  # FastAPI factory, lifespan, CORS, router mount
├── config.py                # Pydantic-Settings (env)
├── logging_config.py
├── api/
│   ├── health.py            # GET /api/health
│   ├── sessions.py          # REST: start / stop / list / get
│   └── websocket.py         # /ws/sessions/{id} loop
├── core/
│   ├── ws_protocol.py       # Pydantic models for ALL WS messages
│   ├── ids.py               # gen_session_id, gen_entry_id
│   └── errors.py
├── services/
│   ├── session_manager.py   # in-memory registry, broadcast helper
│   ├── stt_service.py       # BaseSTTProvider + Mock + OpenRouter + FutureLocal
│   ├── openrouter_service.py# async httpx client, normalize()
│   └── stream_dispatcher.py # bridges provider events → session + WS
└── cp2_stubs/               # NOT imported in CP1
    ├── ocr_service.py
    ├── ai_summary_service.py
    ├── document_generator.py
    └── notifications_service.py
```

### Provider abstraction

`BaseSTTProvider` defines a tiny contract: `register_speakers`, `stream (async iter)`, `stop`.
CP1 ships two concrete providers:

- `MockSTTProvider` — deterministic 12-utterance Russian script with the same
  partial/final cadence as the frontend mock.
- `OpenRouterSTTProvider` — wraps `MockSTTProvider` and post-processes `FinalEvent`
  text via OpenRouter chat completions.

`FutureLocalSTTProvider` is a CP2 stub that will wrap a local Whisper + pyannote
pipeline. The whole provider swap is a one-line `STT_PROVIDER` env change.

### WebSocket protocol source of truth

`app/core/ws_protocol.py` is the only place message shapes are defined.
The frontend (`frontend/src/lib/wsStt.ts`) mirrors the same shapes.

## Environment

| Var | Default | Notes |
|---|---|---|
| `HOST` | `0.0.0.0` | |
| `PORT` | `8000` | |
| `LOG_LEVEL` | `INFO` | |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated |
| `STT_PROVIDER` | `mock` | `mock` \| `openrouter` \| `future_local` |
| `SCRIPT_LOOP_SEC` | `52` | Mock provider loop length |
| `OPENROUTER_API_KEY` | _empty_ | Empty → graceful degradation (no post-processing) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | |
| `OPENROUTER_MODEL` | `mistralai/mistral-7b-instruct:free` | Any OpenRouter chat model |
| `OPENROUTER_TIMEOUT_S` | `4.0` | Per-request HTTP timeout |

## Graceful degradation

| Failure | Behavior |
|---|---|
| `OPENROUTER_API_KEY` empty | `final.text` equals raw ASR text, `postProcessed: false` |
| OpenRouter 4xx/5xx        | Same — original text returned, warning logged |
| OpenRouter timeout        | Same — original text returned, warning logged |
| Backend down              | Frontend WS auto-reconnects every 1.5s |
| Invalid WS JSON           | Server sends `error: invalid_json`, connection stays open |
| Idle > 45s                | Server closes with 4000; client auto-reconnects |

## Frontend integration

The Vite dev server proxies `/api` and `/ws` to `localhost:8000` (see
`frontend/vite.config.ts`), so `VITE_API_URL` and `VITE_WS_URL` can stay
empty in dev. Set them in production.

The frontend hook `useWsSttStream(active, sessionId)` lives at
`frontend/src/lib/wsStt.ts` and is API-compatible with `useMockSttStream`.
The Sessions page swaps between the two via the `useBackendStt` feature flag
(`frontend/src/lib/featureFlags.ts`).
