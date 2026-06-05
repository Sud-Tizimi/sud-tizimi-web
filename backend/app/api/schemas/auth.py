"""Auth schemas — register, login, me."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .user import UserPublic


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    # The frontend sends ``role``; we accept either via populate_by_name.
    role: str = Field(pattern="^(judge|assistant)$")
    court: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(populate_by_name=True)


class LoginResponse(BaseModel):
    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    user: UserPublic

    model_config = ConfigDict(populate_by_name=True)


class MeResponse(BaseModel):
    user: UserPublic
