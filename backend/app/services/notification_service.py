"""Notification service — append a row to ``notifications``.

Mirrors §17 of case-management.md: three event kinds, one per workflow
transition. We de-duplicate at the application layer because the unique
constraint we considered (``recipient_id, case_id, kind``) would prevent
a judge from being re-notified if a case is re-submitted. The current
schema allows multiple notifications per (recipient, case) — the bell
simply shows the most recent.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.enums import NotificationKind
from ..db.models.notification import Notification


async def notify(
    session: AsyncSession,
    *,
    recipient_id: str,
    case_id: str,
    kind: NotificationKind,
    message_key: str,
    at: Optional[datetime] = None,
) -> Notification:
    n = Notification(
        id=str(uuid.uuid4()),
        recipient_id=recipient_id,
        case_id=case_id,
        kind=kind,
        message_key=message_key,
    )
    if at is not None:
        n.at = at
    session.add(n)
    await session.flush()
    return n
