"""Document schemas — Phase B."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    id: str
    case_id: Optional[str] = Field(default=None, alias="caseId")
    uploader_id: str = Field(alias="uploaderId")
    uploader_name: str = Field(alias="uploaderName")
    file_name: str = Field(alias="fileName")
    file_type: str = Field(alias="fileType")
    size_bytes: int = Field(alias="size")
    category: str
    detected_type: str = Field(alias="detectedType")
    detected_type_label: str = Field(alias="detectedTypeLabel")
    ai_confidence: int = Field(alias="aiConfidence")
    uploaded_at: datetime = Field(alias="uploadedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DocumentAttachRequest(BaseModel):
    case_id: str = Field(alias="caseId")

    model_config = ConfigDict(populate_by_name=True)
