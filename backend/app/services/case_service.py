"""Case service — DB-side case CRUD + workflow state machine.

State transitions are enforced here, NOT in the router. Side effects
(activity + notifications) are written in the same transaction as the
status change, so a partial failure rolls back everything.

State machine:

    draft        ──submit──▶ under_review ──approve──▶ approved
    returned     ──submit──▶ under_review ──return ──▶ returned
    approved     ──return──▶ returned    (post-approval correction)
    under_review ──return──▶ returned
    approved|returned ──reopen──▶ draft    (Phase B / reserved)

All transitions are reversible from a workflow standpoint: ``submit``
can fire from ``draft`` or ``returned``; ``return`` from ``under_review``
or ``approved``; ``approve`` only from ``under_review``; ``reopen`` only
from ``approved`` or ``returned``.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.enums import (
    ActivityType,
    CaseStatus,
    NotificationKind,
    UserRole,
)
from ..db.models.case import Case
from ..db.models.user import User
from . import activity_service, notification_service


# ---------------------------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------------------------

async def list_cases_for_user(session: AsyncSession, user: User) -> list[Case]:
    """Return cases visible to ``user``.

    Judges see cases where they are the assigned judge; assistants see
    cases where they are the assistant. No cross-role leakage.
    """
    stmt = select(Case)
    if user.role == UserRole.JUDGE:
        stmt = stmt.where(Case.assigned_judge_id == user.id)
    else:
        stmt = stmt.where(Case.assistant_id == user.id)
    stmt = stmt.order_by(Case.updated_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_case_in_scope(
    session: AsyncSession, case_id: str, user: User
) -> Case:
    """Fetch a case if it's in the user's scope, else 404 (to avoid leaking
    the existence of cases the user cannot see)."""
    case = await session.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")
    if user.role == UserRole.JUDGE and case.assigned_judge_id != user.id:
        raise HTTPException(status_code=404, detail="case_not_found")
    if user.role == UserRole.ASSISTANT and case.assistant_id != user.id:
        raise HTTPException(status_code=404, detail="case_not_found")
    return case


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def create_case(
    session: AsyncSession,
    *,
    actor: User,
    case_number: str,
    citizen_name: str,
    description: str,
    assigned_judge_id: str,
) -> Case:
    """Assistants create a case. Status starts as ``draft``."""
    if actor.role != UserRole.ASSISTANT:
        raise HTTPException(status_code=403, detail="forbidden")
    # Verify the judge exists and is actually a judge.
    judge = await session.get(User, assigned_judge_id)
    if judge is None or judge.role != UserRole.JUDGE:
        raise HTTPException(status_code=400, detail="invalid_judge")
    # Uniqueness on case_number.
    existing = await session.execute(
        select(Case).where(Case.case_number == case_number)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="case_number_taken")

    case = Case(
        id=str(uuid.uuid4()),
        case_number=case_number,
        citizen_name=citizen_name,
        description=description,
        status=CaseStatus.DRAFT,
        assigned_judge_id=judge.id,
        assistant_id=actor.id,
    )
    session.add(case)
    await session.flush()
    # Pull DB-generated server defaults (created_at/updated_at) into the
    # Python object NOW, while the session is still active. Otherwise
    # Pydantic's from_attributes=True triggers a lazy refresh AFTER the
    # session closes → MissingGreenlet on async.
    await session.refresh(case, ["created_at", "updated_at"])

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.CASE_CREATED,
        actor_id=actor.id,
        message_key="activity.case_created",
    )
    return case


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

async def update_case(
    session: AsyncSession,
    *,
    actor: User,
    case_id: str,
    case_number: Optional[str] = None,
    citizen_name: Optional[str] = None,
    description: Optional[str] = None,
    assigned_judge_id: Optional[str] = None,
) -> Case:
    """Edit a case. Only the owning assistant can do it, and only while the
    case is in ``draft`` or ``returned`` (i.e. not under review / approved).
    A no-op request (no field provided) is rejected with 400.

    The ``case_number`` and ``assigned_judge_id`` re-validations mirror the
    create flow (uniqueness + role). Partial updates leave unspecified
    fields unchanged.
    """
    case = await get_case_in_scope(session, case_id, actor)
    if actor.role != UserRole.ASSISTANT or case.assistant_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if case.status not in (CaseStatus.DRAFT, CaseStatus.RETURNED):
        raise HTTPException(
            status_code=409,
            detail="case_locked:only_draft_or_returned_can_be_edited",
        )

    if (
        case_number is None
        and citizen_name is None
        and description is None
        and assigned_judge_id is None
    ):
        raise HTTPException(status_code=400, detail="no_fields_to_update")

    if case_number is not None and case_number != case.case_number:
        existing = await session.execute(
            select(Case).where(Case.case_number == case_number)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="case_number_taken")
        case.case_number = case_number

    if assigned_judge_id is not None and assigned_judge_id != case.assigned_judge_id:
        judge = await session.get(User, assigned_judge_id)
        if judge is None or judge.role != UserRole.JUDGE:
            raise HTTPException(status_code=400, detail="invalid_judge")
        case.assigned_judge_id = judge.id

    if citizen_name is not None:
        case.citizen_name = citizen_name
    if description is not None:
        case.description = description

    case.updated_at = datetime.utcnow()
    await session.flush()

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.CASE_EDITED,
        actor_id=actor.id,
        message_key="activity.case_edited",
    )
    return case


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def delete_case(
    session: AsyncSession, *, actor: User, case_id: str
) -> None:
    """Delete a case. Only the owning assistant can do it, and only while
    the case is still in ``draft`` (a case that's already been submitted,
    approved, or returned lives on the audit trail).

    Attached documents are NOT deleted — the ``documents.case_id`` FK is
    declared ``ON DELETE SET NULL``, so they simply become orphans visible
    in ``/documents?scope=mine`` for re-attachment or final cleanup.

    We intentionally do NOT write a ``case_deleted`` activity row: the
    ``activity_events.case_id`` FK is ``ON DELETE CASCADE``, so such a row
    would be erased in the same transaction and the audit breadcrumb would
    never land anywhere.
    """
    case = await get_case_in_scope(session, case_id, actor)
    if actor.role != UserRole.ASSISTANT or case.assistant_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if case.status != CaseStatus.DRAFT:
        raise HTTPException(
            status_code=409,
            detail="case_locked:only_draft_can_be_deleted",
        )

    await session.delete(case)
    await session.flush()


# ---------------------------------------------------------------------------
# Workflow transitions
# ---------------------------------------------------------------------------

async def submit_case(
    session: AsyncSession, *, case_id: str, actor: User
) -> Case:
    """draft|returned → under_review. Actor must be the case's assistant."""
    case = await get_case_in_scope(session, case_id, actor)
    if actor.role != UserRole.ASSISTANT or case.assistant_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if case.status not in (CaseStatus.DRAFT, CaseStatus.RETURNED):
        raise HTTPException(status_code=409, detail="invalid_transition")

    case.status = CaseStatus.UNDER_REVIEW
    case.return_reason = None
    case.updated_at = datetime.utcnow()
    await session.flush()

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.CASE_SUBMITTED,
        actor_id=actor.id,
        message_key="activity.case_submitted",
    )
    await notification_service.notify(
        session,
        recipient_id=case.assigned_judge_id,
        case_id=case.id,
        kind=NotificationKind.CASE_SUBMITTED_TO_JUDGE,
        message_key="notification.case_submitted_to_judge",
    )
    return case


async def approve_case(
    session: AsyncSession, *, case_id: str, actor: User
) -> Case:
    """under_review → approved. Actor must be the case's judge."""
    case = await get_case_in_scope(session, case_id, actor)
    if actor.role != UserRole.JUDGE or case.assigned_judge_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if case.status != CaseStatus.UNDER_REVIEW:
        raise HTTPException(status_code=409, detail="invalid_transition")

    case.status = CaseStatus.APPROVED
    case.return_reason = None
    case.updated_at = datetime.utcnow()
    await session.flush()

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.CASE_APPROVED,
        actor_id=actor.id,
        message_key="activity.case_approved",
    )
    await notification_service.notify(
        session,
        recipient_id=case.assistant_id,
        case_id=case.id,
        kind=NotificationKind.CASE_APPROVED,
        message_key="notification.case_approved",
    )
    return case


async def return_case(
    session: AsyncSession, *, case_id: str, actor: User, reason: str
) -> Case:
    """under_review|approved → returned. Actor must be the case's judge."""
    case = await get_case_in_scope(session, case_id, actor)
    if actor.role != UserRole.JUDGE or case.assigned_judge_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if case.status not in (CaseStatus.UNDER_REVIEW, CaseStatus.APPROVED):
        raise HTTPException(status_code=409, detail="invalid_transition")

    case.status = CaseStatus.RETURNED
    case.return_reason = reason
    case.updated_at = datetime.utcnow()
    await session.flush()

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.CASE_RETURNED,
        actor_id=actor.id,
        message_key="activity.case_returned",
    )
    await notification_service.notify(
        session,
        recipient_id=case.assistant_id,
        case_id=case.id,
        kind=NotificationKind.CASE_RETURNED_TO_ASSISTANT,
        message_key="notification.case_returned_to_assistant",
    )
    return case


async def reopen_case(
    session: AsyncSession, *, case_id: str, actor: User
) -> Case:
    """approved|returned → draft. Reserved for Phase B UI; the endpoint is
    exposed now so the router surface is stable.

    The judge (whoever returned or approved the case) is the only one who
    can revert the workflow to ``draft``.
    """
    case = await get_case_in_scope(session, case_id, actor)
    if actor.role != UserRole.JUDGE or case.assigned_judge_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if case.status not in (CaseStatus.APPROVED, CaseStatus.RETURNED):
        raise HTTPException(status_code=409, detail="invalid_transition")

    case.status = CaseStatus.DRAFT
    case.return_reason = None
    case.updated_at = datetime.utcnow()
    await session.flush()
    return case
