"""Activity feed router — per-case timeline (case-management.md §11)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.enums import UserRole
from ..db import get_db
from ..db.models.activity import ActivityEvent
from ..db.models.case import Case
from ..db.models.user import User
from .deps import get_current_user
from .schemas.activity import ActivityEventResponse, ActivityListResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=ActivityListResponse)
async def list_activity(
    caseId: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityListResponse:
    """Return timeline events for ``caseId``, ordered newest first.

    Scope check: the case must be visible to the current user (judge sees
    only their assigned; assistant sees only their own). 404 (not 403) to
    avoid leaking the existence of cases the user cannot see.
    """
    case = await session.get(Case, caseId)
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")
    if user.role == UserRole.JUDGE and case.assigned_judge_id != user.id:
        raise HTTPException(status_code=404, detail="case_not_found")
    if user.role == UserRole.ASSISTANT and case.assistant_id != user.id:
        raise HTTPException(status_code=404, detail="case_not_found")

    res = await session.execute(
        select(ActivityEvent, User.full_name, User.role)
        .join(User, User.id == ActivityEvent.actor_id)
        .where(ActivityEvent.case_id == caseId)
        .order_by(ActivityEvent.at.desc(), ActivityEvent.id.desc())
    )
    return ActivityListResponse(
        events=[
            ActivityEventResponse.model_validate(
                {
                    "id": event.id,
                    "caseId": event.case_id,
                    "type": event.type.value,
                    "actorId": event.actor_id,
                    "actorName": actor_name,
                    "actorRole": actor_role.value,
                    "messageKey": event.message_key,
                    "meta": event.meta,
                    "at": event.at,
                }
            )
            for event, actor_name, actor_role in res.all()
        ]
    )
