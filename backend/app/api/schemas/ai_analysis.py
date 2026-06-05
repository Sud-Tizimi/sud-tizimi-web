"""SudAI-Law-UZ response/request schemas and a document-type mapper.

The eight Pydantic models below are the wire format produced by
``app.services.ai_law.pipeline`` — they originate from the standalone
SudAI MVP (``sudai-research-raw/app/schemas.py``) and have been renamed
with an ``AI`` prefix to avoid name clashes with future modules
(recommendation, settlement, mediation).

The DB-persisting record wrapper (``AIAnalysisRecord``) is the shape the
HTTP router returns to the frontend; the heavy AI result lives inside
``result`` and is only fetched on demand by the AI panel.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    AnonymizationLabel,
    CaseLegalCategory,
    DocumentLanguage,
    ProcedureType,
)


# ---------------------------------------------------------------------------
# Plain text endpoint — kept for parity with the standalone SudAI MVP
# ---------------------------------------------------------------------------


class AITextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    filename: Optional[str] = None


# ---------------------------------------------------------------------------
# Core AI analysis payload
# ---------------------------------------------------------------------------


class AIDocumentMetadata(BaseModel):
    document_type: str
    language: DocumentLanguage
    pages: int
    ocr_required: bool


class AIAnonymizationEntity(BaseModel):
    label: AnonymizationLabel
    original: str
    placeholder: str


class AIExtractedLegalObjects(BaseModel):
    claimant: Optional[str] = None
    respondent: Optional[str] = None
    claim_subject: Optional[str] = None
    demand_summary: Optional[str] = None
    contract_number: Optional[str] = None
    debt_amount: Optional[str] = None
    dates: List[str] = []
    attachments: List[str] = []


class AIClassificationResult(BaseModel):
    main_category: CaseLegalCategory
    sub_category: str
    procedure_type: ProcedureType
    confidence: float


class AIMatchedSource(BaseModel):
    law: str
    article: str
    title: str
    excerpt: str
    relevance: float
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    category_path: Optional[str] = None


class AIRecommendation(BaseModel):
    status: str
    recommendation: str
    risk: str


class AIAnalysisResponse(BaseModel):
    """Envelope returned by ``app.services.ai_law.pipeline.analyze_*``."""

    metadata: AIDocumentMetadata
    anonymized_text: str
    anonymized_entities: List[AIAnonymizationEntity]
    extracted_objects: AIExtractedLegalObjects
    classification: AIClassificationResult
    matched_sources: List[AIMatchedSource]
    explanation: str
    confidence_percent: int
    human_review: AIRecommendation


# ---------------------------------------------------------------------------
# Request/response wrappers for the HTTP router
# ---------------------------------------------------------------------------


class AICaseAnalysisRequest(BaseModel):
    """Body for ``POST /api/cases/{case_id}/analysis``. Empty for now — the
    request is just a trigger; the case is resolved from the path.
    """

    model_config = ConfigDict(extra="forbid")


class AIDocumentAnalysisRequest(BaseModel):
    """Body for ``POST /api/documents/{doc_id}/analysis``. Empty trigger."""

    model_config = ConfigDict(extra="forbid")


class AIAnalysisRecord(BaseModel):
    """Stored result of a single AI analysis run (per-document or per-case).

    ``result`` is the full ``AIAnalysisResponse`` payload — large but
    convenient, and we keep history so users can compare reruns.
    """

    id: str
    caseId: str
    documentId: Optional[str] = None
    status: str
    provider: str
    startedAt: datetime
    finishedAt: Optional[datetime] = None
    errorMessage: Optional[str] = None
    result: Optional[dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AIAnalysisRecordList(BaseModel):
    """List wrapper — keeps the wire format consistent with other list
    endpoints in the codebase.
    """

    records: List[AIAnalysisRecord]
