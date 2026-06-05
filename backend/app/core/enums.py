"""String enums shared across DB models, services, and Pydantic schemas.

DB columns store the ``value`` (snake_case). Pydantic schemas use
``alias=…`` to map these to camelCase keys on the JSON wire where the
frontend expects them (e.g. ``case_decision`` ↔ ``caseDecision``).
"""
from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    """A user account is either a judge or an assistant (kotib)."""

    JUDGE = "judge"
    ASSISTANT = "assistant"


class CaseStatus(str, Enum):
    """Case workflow state — see case-management.md §4."""

    DRAFT = "draft"
    UPLOADED = "uploaded"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    RETURNED = "returned"


class DocumentCategory(str, Enum):
    """Top-level grouping of a case document — see case-management.md §7."""

    PROCEDURAL = "procedural"
    PARTICIPANT = "participant"
    EVIDENCE = "evidence"
    COURT = "court"


class DocumentType(str, Enum):
    """Specific document kinds — see case-management.md §7.1–§7.4."""

    # Procedural
    CLAIM = "claim"
    COUNTERCLAIM = "counterclaim"
    APPEAL = "appeal"
    CASSATION_APPEAL = "cassation_appeal"
    STATEMENT = "statement"
    # Participant
    EXPLANATION = "explanation"
    OBJECTION = "objection"
    ADDITIONAL_STATEMENT = "additional_statement"
    # Evidence
    CONTRACT = "contract"
    FINANCIAL_DOCUMENT = "financial_document"
    PERSONAL_DOCUMENT = "personal_document"
    # Court
    COURT_DECISION = "court_decision"
    COURT_RESOLUTION = "court_resolution"
    HEARING_TRANSCRIPT = "hearing_transcript"


class DocumentFileType(str, Enum):
    """Allowed file extensions — see case-management.md §8."""

    PDF = "pdf"
    DOCX = "docx"
    JPG = "jpg"
    PNG = "png"


class ActivityType(str, Enum):
    """Timeline event kinds — one per workflow transition or document change."""

    CASE_CREATED = "case_created"
    CASE_EDITED = "case_edited"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DOCUMENTS_CLASSIFIED = "documents_classified"
    CASE_SUBMITTED = "case_submitted"
    CASE_APPROVED = "case_approved"
    CASE_RETURNED = "case_returned"
    DOCUMENT_ADDED = "document_added"
    DOCUMENT_REMOVED = "document_removed"
    # Phase 27 — SudAI-Law-UZ
    AI_DOCUMENT_ANALYSIS_REQUESTED = "ai_document_analysis_requested"
    AI_DOCUMENT_ANALYSIS_COMPLETED = "ai_document_analysis_completed"
    AI_DOCUMENT_ANALYSIS_FAILED = "ai_document_analysis_failed"
    AI_CASE_ANALYSIS_REQUESTED = "ai_case_analysis_requested"
    AI_CASE_ANALYSIS_COMPLETED = "ai_case_analysis_completed"
    AI_CASE_ANALYSIS_FAILED = "ai_case_analysis_failed"


class AIAnalysisStatus(str, Enum):
    """Lifecycle of a SudAI analysis run."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class CaseLegalCategory(str, Enum):
    """Top-level legal category assigned by SudAI classifier.

    Values are stored snake_case in the database and surfaced to the UI
    via i18n keys (``aiAnalysis.category.*``). They are intentionally
    distinct from ``DocumentType`` — the classifier outputs a procedural
    category (the kind of dispute), not a document type.
    """

    OILAVIY_NIZO = "oilaviy_nizo"
    MEHNAT_NIZOSI = "mehnat_nizosi"
    MAMURIY_YOKI_IQTISODIY_NIZO = "mamuriy_yoki_iqtisodiy_nizo"
    FUQAROLIK_ISHI = "fuqarolik_ishi"
    UMUMIY_HUQUQIY_MUROJAAT = "umumiy_huquqiy_murojaat"


class ProcedureType(str, Enum):
    """Which court procedure the case is likely to follow."""

    FUQAROLIK_SUD = "fuqarolik_sud"
    MAMURIY_YOKI_IQTISODIY_SUD = "mamuriy_yoki_iqtisodiy_sud"
    SUD_XODIMI_ANIQLAYDI = "sud_xodimi_aniqlaydi"


class DocumentLanguage(str, Enum):
    """Detected language of an analysed document."""

    UZBEK_LATIN = "uzbek_latin"
    UZBEK_CYRILLIC_OR_RUSSIAN = "uzbek_cyrillic_or_russian"


class AnonymizationLabel(str, Enum):
    """PII/PHI categories detected by the anonymizer."""

    PHONE = "phone"
    PASSPORT = "passport"
    JSHSHIR = "jshshir"
    STIR = "stir"
    ADDRESS = "address"
    FISH = "fish"


class NotificationKind(str, Enum):
    """In-system notification types — see case-management.md §17."""

    CASE_SUBMITTED_TO_JUDGE = "case_submitted_to_judge"
    CASE_RETURNED_TO_ASSISTANT = "case_returned_to_assistant"
    CASE_APPROVED = "case_approved"
