"""WebSocket endpoint — the realtime heart of the system.

The server simulates audio/STT internally in CP1. The client only sends
control messages (ping, register_speakers, subscribe_audio_level); no
binary frames are accepted in CP1.

Wire contract is defined in `app/core/ws_protocol.py`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.ws_protocol import (
    ClientPong,
    ClientRegisterSpeakers,
    ClientSubscribeAudioLevel,
    ServerSpeakerRegistered,
    make_error,
    make_session_ready,
    parse_client_message,
)
from ..services.session_manager import SessionManager

router = APIRouter()
log = logging.getLogger("ws")

HEARTBEAT_INTERVAL_S = 20.0
IDLE_TIMEOUT_S = 45.0


@router.websocket("/ws/sessions/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    sm: SessionManager = websocket.app.state.session_manager
    sess = sm.get(session_id)
    if sess is None or sess.stopped:
        await websocket.close(code=4404, reason="session_not_found")
        return

    await websocket.accept()
    attached = await sm.attach_socket(session_id, websocket)
    if not attached:
        await websocket.close(code=4404, reason="session_unavailable")
        return

    loop = asyncio.get_event_loop()
    last_inbound = loop.time()
    heartbeat_task: asyncio.Task | None = None

    async def heartbeat() -> None:
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)
                try:
                    await websocket.send_json(
                        {"type": "ping", "t": loop.time()}
                    )
                except Exception:
                    return
        except asyncio.CancelledError:
            return

    heartbeat_task = asyncio.create_task(heartbeat(), name=f"hb-{session_id}")

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            last_inbound = loop.time()

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(make_error("invalid_json").model_dump())
                continue

            try:
                msg = parse_client_message(payload)
            except ValueError as e:
                await websocket.send_json(make_error(str(e)).model_dump())
                continue

            await _handle_client_message(sm, session_id, websocket, msg)

            if loop.time() - last_inbound > IDLE_TIMEOUT_S:
                await websocket.close(code=4000, reason="idle_timeout")
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws_crash sid=%s", session_id)
        try:
            await websocket.send_json(
                make_error("internal_error").model_dump()
            )
        except Exception:
            pass
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except (asyncio.CancelledError, Exception):
                pass
        await sm.detach_socket(session_id, websocket)


async def _handle_client_message(
    sm: SessionManager,
    session_id: str,
    websocket: WebSocket,
    msg,  # type: ignore[no-untyped-def]
) -> None:
    if isinstance(msg, ClientPong):
        # Heartbeat reply — nothing to do
        return

    if isinstance(msg, ClientRegisterSpeakers):
        added = await sm.register_speakers(session_id, msg.speakers)
        for seed in added:
            try:
                await websocket.send_json(
                    ServerSpeakerRegistered(speaker=seed).model_dump()
                )
            except Exception:
                log.debug("send_speaker_registered_failed", exc_info=True)
        return

    if isinstance(msg, ClientSubscribeAudioLevel):
        sess = sm.get(session_id)
        if sess is not None:
            sess.audio_level_enabled = msg.enabled
        return

    # Anything else (e.g. ClientPing) — reply with pong
    if getattr(msg, "type", None) == "ping":
        try:
            await websocket.send_json(
                {"type": "pong", "t": getattr(msg, "t", time.time())}
            )
        except Exception:
            log.debug("send_pong_failed", exc_info=True)
        return
