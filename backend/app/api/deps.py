"""Shared FastAPI dependencies — auth + role gates."""
from __future__ import annotations

from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.enums import UserRole
from ..core.security import decode_access_token
from ..db import get_db
from ..db.models.user import User

# ``tokenUrl`` is the relative path used by Swagger UI's "Authorize" dialog.
# The frontend posts to the same URL with a form-encoded body.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Decode the bearer token and return the current User. 401 on any failure."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    payload = decode_access_token(token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = await session.get(User, sub)
    if user is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user


def require_role(*allowed: UserRole):
    """Sub-dependency factory: 403 if the current user's role is not in ``allowed``."""

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return _dep


def roles_of(user: User) -> Iterable[UserRole]:
    return [user.role]
