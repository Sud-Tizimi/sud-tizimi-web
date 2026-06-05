"""FastAPI application factory + lifespan."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    activity,
    ai_analyze,
    asr,
    auth,
    cases,
    documents,
    health,
    notifications,
    ocr,
    sessions,
    users,
    websocket,
)
from .config import get_settings
from .db import dispose_engine, init_engine
from .logging_config import setup_logging
from .services.session_manager import SessionManager
from .services.stt_service import build_stt_provider
from .services.stream_dispatcher import StreamDispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    # Phase A — async DB engine. Built here (not at import time) so
    # ``alembic`` can run without an active app context.
    init_engine(settings.database_url)
    log_msg = f"db url = {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}"
    print(log_msg)  # noqa: T201 — boot log

    # CP1 — live STT session pipeline (unchanged).
    provider = build_stt_provider(settings)
    dispatcher = StreamDispatcher()
    app.state.session_manager = SessionManager(
        provider=provider, dispatcher=dispatcher, settings=settings
    )
    try:
        yield
    finally:
        await app.state.session_manager.shutdown_all()
        # If the provider owns a httpx client (OpenRouter), close it.
        inner = getattr(provider, "_inner", None)
        if inner is not None and hasattr(inner, "close"):
            await inner.close()
        if hasattr(provider, "close"):
            await provider.close()
        # Phase A — tear down the async DB engine.
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Sud-Tizimi API",
        version="0.2.0",
        description=(
            "Sud-Tizimi — real-time STT, speaker diarization, "
            "case management with MySQL-backed accounts (Phase A)."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # CP1 (unchanged).
    app.include_router(health.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(websocket.router)
    # Voice ASR cloud/local integration.
    app.include_router(asr.router, prefix="/api")
    # Phase A.
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(cases.router, prefix="/api")
    app.include_router(activity.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    # Phase B.
    app.include_router(documents.router, prefix="/api")
    # Phase 27 — SudAI-Law-UZ legal document analysis.
    app.include_router(ai_analyze.case_router, prefix="/api")
    app.include_router(ai_analyze.doc_router, prefix="/api")
    # Phase D — OCR (UDIP engine ported: PaddleOCR / Tesseract / Gemini / Stub).
    app.include_router(ocr.router, prefix="/api")
    return app


app = create_app()
