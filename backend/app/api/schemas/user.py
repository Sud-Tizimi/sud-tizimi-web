"""User-shaped responses."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str = Field(alias="fullName")
    role: str  # "judge" or "assistant"
    court: str | None = None
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UserListResponse(BaseModel):
    # The shape is ``{judges: [...]}`` or ``{assistants: [...]}`` — the router
    # picks the right key.
    judges: list[UserPublic] | None = None
    assistants: list[UserPublic] | None = None
