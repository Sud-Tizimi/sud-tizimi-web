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
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class AIWireModel(BaseModel):
    """Public SudAI DTO convention: camelCase on the HTTP boundary.

    Pipeline and DB payloads use Pythonic snake_case. ``populate_by_name``
    deliberately accepts those persisted payloads, while ``by_alias=True``
    produces the TypeScript-facing contract in one place.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=_camel_case)


class AIStrictWireModel(AIWireModel):
    """Camel-case DTO whose provider-supplied fields are strictly bounded."""

    model_config = ConfigDict(
        populate_by_name=True, alias_generator=_camel_case, extra="forbid"
    )


class AIDocumentMetadata(AIWireModel):
    document_type: str
    language: DocumentLanguage
    pages: int
    ocr_required: bool
    extraction_method: str = "text"
    ocr_used: bool = False


class AIAnonymizationEntity(AIWireModel):
    label: AnonymizationLabel
    original: str
    placeholder: str


class AIExtractedLegalObjects(AIWireModel):
    claimant: Optional[str] = None
    respondent: Optional[str] = None
    claim_subject: Optional[str] = None
    demand_summary: Optional[str] = None
    contract_number: Optional[str] = None
    debt_amount: Optional[str] = None
    dates: List[str] = []
    attachments: List[str] = []


class AIClassificationResult(AIWireModel):
    main_category: CaseLegalCategory
    sub_category: str
    procedure_type: ProcedureType
    confidence: float


class AIMatchedSource(AIWireModel):
    law: str
    article: str
    title: str
    excerpt: str
    relevance: float
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    category_path: Optional[str] = None


class AIRecommendation(AIWireModel):
    model_config = ConfigDict(
        populate_by_name=True, alias_generator=_camel_case, extra="forbid"
    )

    status: str
    recommendation: str
    risk: str


class AILegalFinding(AIWireModel):
    """A model finding whose legal assertions cite only retrieval source IDs."""

    model_config = ConfigDict(
        populate_by_name=True, alias_generator=_camel_case, extra="forbid"
    )

    kind: Literal["document_fact", "legal_assessment", "insufficient_context"]
    statement: str = Field(min_length=1, max_length=4000)
    source_ids: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _legal_assessments_require_sources(self):
        if self.kind == "legal_assessment" and not self.source_ids:
            raise ValueError("legal_assessment_requires_source_ids")
        return self


class AIAnalysisTechnicalMetadata(AIWireModel):
    """Execution data, deliberately separated from legal conclusions."""

    analysis_mode: Literal["local", "llm"] = "local"
    provider: str = "local"
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    token_usage: Optional[dict[str, int]] = None


# ---------------------------------------------------------------------------
# Case-level factual synthesis
# ---------------------------------------------------------------------------


CaseAmountType = Literal[
    "asset_value",
    "sale_price",
    "payment",
    "debt",
    "damage",
    "salary",
    "unknown",
]
CaseLegalDomain = Literal[
    "criminal_property",
    "civil_debt",
    "family",
    "labor",
    "tax",
    "administrative",
    "unknown",
]


class AICaseDocumentInput(AIStrictWireModel):
    """One bounded, anonymized document supplied to factual synthesis."""

    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    text: str = Field(min_length=1)


class AICaseFact(AIStrictWireModel):
    fact_id: str = Field(min_length=1, max_length=120)
    statement: str = Field(min_length=1, max_length=4000)
    document_ids: List[str] = Field(min_length=1)


class AICaseTimelineEvent(AIStrictWireModel):
    sequence: int = Field(ge=1)
    event: str = Field(min_length=1, max_length=2000)
    document_ids: List[str] = Field(min_length=1)


class AICaseEvidenceLink(AIStrictWireModel):
    relationship: str = Field(min_length=1, max_length=2000)
    document_ids: List[str] = Field(min_length=2)
    identifiers: List[str] = Field(default_factory=list)


class AICaseEntity(AIStrictWireModel):
    label: str = Field(min_length=1, max_length=500)
    entity_type: str = Field(min_length=1, max_length=120)
    document_ids: List[str] = Field(min_length=1)


class AICaseTypedAmount(AIStrictWireModel):
    amount: str = Field(min_length=1, max_length=200)
    currency: str = Field(min_length=1, max_length=32)
    amount_type: CaseAmountType
    context: str = Field(min_length=1, max_length=1000)
    document_ids: List[str] = Field(min_length=1)


class AICandidateLegalDomain(AIStrictWireModel):
    domain: CaseLegalDomain
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=2000)


class AICaseFactualSynthesis(AIStrictWireModel):
    """Facts only: no statutes, articles, citations, or provider-owned sources."""

    document_ids: List[str] = Field(min_length=1)
    facts: List[AICaseFact] = Field(default_factory=list)
    timeline: List[AICaseTimelineEvent] = Field(default_factory=list)
    evidence_links: List[AICaseEvidenceLink] = Field(default_factory=list)
    entities: List[AICaseEntity] = Field(default_factory=list)
    amounts: List[AICaseTypedAmount] = Field(default_factory=list)
    candidate_legal_domains: List[AICandidateLegalDomain] = Field(min_length=1)
    legal_issues: List[str] = Field(default_factory=list)
    retrieval_terms: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)


class AICaseReasoningOutput(AIStrictWireModel):
    """Structured second-pass output over synthesis and trusted RAG context."""

    primary_conclusion: str = Field(min_length=1, max_length=8000)
    explanation: str = Field(min_length=1, max_length=8000)
    evidence_summary: List[str] = Field(default_factory=list)
    confidence_percent: int = Field(ge=0, le=100)
    human_review: AIRecommendation
    findings: List[AILegalFinding] = Field(default_factory=list)
    context_sufficient: bool


class AIAnalysisResponse(AIWireModel):
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
    findings: List[AILegalFinding] = Field(default_factory=list)
    technical_metadata: AIAnalysisTechnicalMetadata = Field(
        default_factory=AIAnalysisTechnicalMetadata
    )
    # Case-only extensions. They remain optional so the document response and
    # persisted historical payloads keep validating unchanged.
    factual_synthesis: Optional[AICaseFactualSynthesis] = None
    primary_conclusion: Optional[str] = None
    evidence_summary: List[str] = Field(default_factory=list)
    timeline: List[AICaseTimelineEvent] = Field(default_factory=list)
    evidence_links: List[AICaseEvidenceLink] = Field(default_factory=list)
    typed_amounts: List[AICaseTypedAmount] = Field(default_factory=list)
    candidate_legal_domains: List[AICandidateLegalDomain] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)


class AIReasoningOutput(AIWireModel):
    """The only structured shape accepted from an LLM provider."""

    model_config = ConfigDict(
        populate_by_name=True, alias_generator=_camel_case, extra="forbid"
    )

    explanation: str = Field(min_length=1, max_length=8000)
    confidence_percent: int = Field(ge=0, le=100)
    human_review: AIRecommendation
    findings: List[AILegalFinding] = Field(default_factory=list)
    context_sufficient: bool


def analysis_result_to_api(result_json: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert the stored snake_case pipeline payload to the public DTO.

    ``sub_failures`` is a case-level persistence extension rather than part of
    the per-document pipeline response, so preserve it explicitly under the
    same camelCase HTTP convention.
    """
    if result_json is None:
        return None
    result = AIAnalysisResponse.model_validate(result_json).model_dump(
        mode="json", by_alias=True
    )
    if "sub_failures" in result_json:
        result["subFailures"] = result_json["sub_failures"]
    return result


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
