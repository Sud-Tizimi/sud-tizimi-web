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
    DOCUMENTS_UPLOADED = "documents_uploaded"
    DOCUMENTS_CLASSIFIED = "documents_classified"
    CASE_SUBMITTED = "case_submitted"
    CASE_APPROVED = "case_approved"
    CASE_RETURNED = "case_returned"
    DOCUMENT_ADDED = "document_added"
    DOCUMENT_REMOVED = "document_removed"


class NotificationKind(str, Enum):
    """In-system notification types — see case-management.md §17."""

    CASE_SUBMITTED_TO_JUDGE = "case_submitted_to_judge"
    CASE_RETURNED_TO_ASSISTANT = "case_returned_to_assistant"
    CASE_APPROVED = "case_approved"
