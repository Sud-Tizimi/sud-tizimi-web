"""Activity-event service — append a row to ``activity_events``.

Used by case-service transitions; the caller is responsible for
committing the session (we keep all side effects in a single transaction).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.enums import ActivityType
from ..db.models.activity import ActivityEvent


async def record_event(
    session: AsyncSession,
    *,
    case_id: str,
    type: ActivityType,
    actor_id: str,
    message_key: str,
    meta: Optional[dict[str, Any]] = None,
    at: Optional[datetime] = None,
) -> ActivityEvent:
    """Insert a new activity event. ``at`` defaults to server now() when None
    so callers writing historical events (like the seed) can pass an
    explicit timestamp.
    """
    ev = ActivityEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        type=type,
        actor_id=actor_id,
        message_key=message_key,
        meta=meta,
    )
    if at is not None:
        # The column has a server_default but not server_onupdate; we set
        # the Python-side value so historical events respect ``at``.
        ev.at = at
    session.add(ev)
    await session.flush()
    return ev
