"""Liveness / readiness endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe — always returns ok if the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict:
    """Readiness probe — in CP1 we have no external deps, so always ready."""
    return {"ready": True}
