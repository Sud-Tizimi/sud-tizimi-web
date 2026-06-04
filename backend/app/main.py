"""FastAPI application factory + lifespan."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import health, sessions, websocket
from .config import get_settings
from .logging_config import setup_logging
from .services.session_manager import SessionManager
from .services.stt_service import build_stt_provider
from .services.stream_dispatcher import StreamDispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

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


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Sud-Tizimi API",
        version="0.1.0",
        description=(
            "CP1 MVP backend for Sud-Tizimi — real-time STT, "
            "speaker diarization, and OpenRouter post-processing."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(websocket.router)
    return app


app = create_app()
