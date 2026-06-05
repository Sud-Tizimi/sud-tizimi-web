"""User directory router — for the case-create form to populate dropdowns."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.enums import UserRole
from ..db import get_db
from ..db.models.user import User
from .deps import get_current_user
from .schemas.user import UserListResponse, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


def _to_public(user: User) -> UserPublic:
    return UserPublic.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "fullName": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "court": user.court,
            "createdAt": user.created_at,
        }
    )


@router.get("/judges", response_model=UserListResponse)
async def list_judges(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> UserListResponse:
    res = await session.execute(
        select(User).where(User.role == UserRole.JUDGE).order_by(User.full_name.asc())
    )
    return UserListResponse(judges=[_to_public(u) for u in res.scalars().all()])


@router.get("/assistants", response_model=UserListResponse)
async def list_assistants(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> UserListResponse:
    res = await session.execute(
        select(User).where(User.role == UserRole.ASSISTANT).order_by(User.full_name.asc())
    )
    return UserListResponse(assistants=[_to_public(u) for u in res.scalars().all()])
