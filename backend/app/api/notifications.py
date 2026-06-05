"""Notifications router — list + mark read."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.models.notification import Notification
from ..db.models.user import User
from .deps import get_current_user
from .schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    ReadAllResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_mine(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationListResponse:
    res = await session.execute(
        select(Notification)
        .where(Notification.recipient_id == user.id)
        .order_by(Notification.at.desc())
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in res.scalars().all()]
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationResponse:
    n = await session.get(Notification, notification_id)
    if n is None or n.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="notification_not_found")
    if not n.read:
        n.read = True
        await session.commit()
    return NotificationResponse.model_validate(n)


@router.post("/read-all", response_model=ReadAllResponse)
async def mark_all_read(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReadAllResponse:
    res = await session.execute(
        update(Notification)
        .where(Notification.recipient_id == user.id, Notification.read.is_(False))
        .values(read=True)
    )
    await session.commit()
    return ReadAllResponse(updated=res.rowcount or 0)
