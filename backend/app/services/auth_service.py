"""Auth business logic — register and authenticate.

Side effects: writes to ``users``. The JWT itself is minted in
``app.core.security`` and the router stitches together the response.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.enums import UserRole
from ..core.security import hash_password, verify_password
from ..db.models.user import User


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    res = await session.execute(select(User).where(User.email == email.lower()))
    return res.scalar_one_or_none()


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    court: str | None,
) -> User:
    """Create a new user. Caller is responsible for committing the session."""
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        court=court,
    )
    session.add(user)
    await session.flush()
    return user


async def authenticate_user(
    session: AsyncSession, *, email: str, password: str
) -> Optional[User]:
    """Return the User if credentials match, else None."""
    user = await get_user_by_email(session, email)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
