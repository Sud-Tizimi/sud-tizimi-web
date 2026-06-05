"""Notification schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    id: str
    case_id: str = Field(alias="caseId")
    kind: str
    message_key: str = Field(alias="messageKey")
    read: bool
    at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class ReadAllResponse(BaseModel):
    updated: int
