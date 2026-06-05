"""Activity event schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActivityEventResponse(BaseModel):
    id: str
    case_id: str = Field(alias="caseId")
    type: str
    actor_id: str = Field(alias="actorId")
    actor_name: str = Field(alias="actorName")
    actor_role: str = Field(alias="actorRole")
    message_key: str = Field(alias="messageKey")
    meta: dict[str, Any] | None = None
    at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ActivityListResponse(BaseModel):
    events: list[ActivityEventResponse]
