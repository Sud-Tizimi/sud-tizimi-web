"""Async SQLAlchemy engine + session factory.

The engine is built lazily (in ``app.main`` lifespan) because we need
``get_settings()`` at runtime and don't want the import side-effect of
opening connections at module import time.

``get_db`` is the FastAPI dependency — yields an ``AsyncSession`` and
guarantees ``close()`` runs after the request.
"""
from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import get_settings

# Module-level engine placeholder. Populated by ``init_engine()`` from the
# FastAPI lifespan so the first DB call doesn't pay the connect cost.
engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> AsyncEngine:
    """Build the async engine and session factory. Called from the lifespan."""
    global engine, AsyncSessionLocal
    engine = create_async_engine(
        database_url,
        pool_recycle=1800,
        future=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine


async def dispose_engine() -> None:
    """Close the engine's connection pool. Called from the lifespan teardown."""
    global engine, AsyncSessionLocal
    if engine is not None:
        await engine.dispose()
    engine = None
    AsyncSessionLocal = None


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields an ``AsyncSession`` and closes it after."""
    if AsyncSessionLocal is None:
        # Defer init so the very first request (e.g. health) works before lifespan
        # has run, in case the operator runs uvicorn without the lifespan hook.
        init_engine(get_settings().database_url)
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
