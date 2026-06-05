"""Case CRUD + workflow schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CaseResponse(BaseModel):
    id: str
    case_number: str = Field(alias="caseNumber")
    citizen_name: str = Field(alias="citizenName")
    description: str
    status: str
    assigned_judge_id: str = Field(alias="assignedJudgeId")
    assistant_id: str = Field(alias="assistantId")
    return_reason: str | None = Field(default=None, alias="returnReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CaseListResponse(BaseModel):
    cases: list[CaseResponse]


class CaseCreateRequest(BaseModel):
    case_number: str = Field(alias="caseNumber", min_length=1, max_length=64)
    citizen_name: str = Field(alias="citizenName", min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000)
    assigned_judge_id: str = Field(alias="assignedJudgeId")

    model_config = ConfigDict(populate_by_name=True)


class CaseUpdateRequest(BaseModel):
    """PATCH body for editing a case. All fields are optional, but at least
    one must be present (enforced in the service layer)."""
    case_number: str | None = Field(default=None, alias="caseNumber", min_length=1, max_length=64)
    citizen_name: str | None = Field(default=None, alias="citizenName", min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    assigned_judge_id: str | None = Field(default=None, alias="assignedJudgeId")

    model_config = ConfigDict(populate_by_name=True)


class CaseReturnRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=2_000)


class StatusTransitionResponse(BaseModel):
    case: CaseResponse
    # Reserved for future fields the frontend may need on a transition
    # (e.g. notifications triggered, side effects).
    meta: dict[str, Any] | None = None
