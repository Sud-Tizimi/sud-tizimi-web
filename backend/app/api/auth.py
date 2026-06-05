"""Auth router — register, login, me."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.enums import UserRole
from ..core.security import create_access_token
from ..db import get_db
from ..db.models.user import User
from ..services import auth_service
from .deps import get_current_user
from .schemas.auth import LoginResponse, MeResponse, RegisterRequest
from .schemas.user import UserPublic

log = logging.getLogger("api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


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


def _mint_token(user: User) -> str:
    settings = get_settings()
    role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    return create_access_token(
        sub=user.id,
        role=role,
        email=user.email,
        expires_minutes=settings.jwt_expire_minutes,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/register", response_model=MeResponse, status_code=201)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_db)
) -> MeResponse:
    """Create a new account. Email must be unique; password ≥ 8 chars."""
    existing = await auth_service.get_user_by_email(session, payload.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="email_taken")
    role = UserRole(payload.role)
    user = await auth_service.register_user(
        session,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=role,
        court=payload.court,
    )
    await session.commit()
    return MeResponse(user=_to_public(user))


@router.post("/login", response_model=LoginResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """OAuth2 form login. ``username`` carries the email (a FastAPI form
    convention). Returns the JWT and the public user profile.
    """
    user = await auth_service.authenticate_user(
        session, email=form.username, password=form.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _mint_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=_to_public(user),
    )


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=_to_public(user))
