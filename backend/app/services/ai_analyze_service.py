"""SudAI-Law-UZ analysis service — runs the pipeline and persists results.

This is the only layer that knows about both
``app.services.ai_law.pipeline`` (pure functions) and the SQLAlchemy ORM
(``ai_analyses`` table). The HTTP router in
``app.api.ai_analyze`` calls into this module.

* :func:`analyze_document` — analyse a single document. Permission: any
  user in the case's scope (judge assigned, or owning assistant).
* :func:`analyze_case_documents` — synthesize and analyse all documents as one
  case. Same permission rules.
* :func:`list_analyses_for_case` / :func:`list_analyses_for_document` —
  history for the AI panel.
* :func:`get_latest_*` — convenience for the UI's "last result" view.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.schemas.ai_analysis import (
    AIAnalysisRecord,
    AIAnalysisResponse,
    analysis_result_to_api,
)
from ..config import get_settings
from ..core.enums import ActivityType, AIAnalysisStatus, UserRole
from ..core.storage import resolve_storage_path
from ..db.models.ai_analysis import AIAnalysis
from ..db.models.case import Case
from ..db.models.document import Document
from ..db.models.user import User
from ..services.ai_law.case_pipeline import (
    CaseDocumentSource,
    analyze_case_documents as pipeline_analyze_case_documents,
)
from ..services.ai_law.document_loader import DocumentExtractionError
from ..services.ai_law.pipeline import analyze_document as pipeline_analyze_document
from . import activity_service, case_service, document_service

_log = logging.getLogger(__name__)

_SAFE_EXTRACTION_ERRORS = {
    "document_text_is_empty",
    "ocr_text_is_empty",
    "all_documents_failed",
}


def _safe_analysis_error(exc: Exception) -> str:
    """Return a client-safe persisted error code without leaking provider detail."""
    if isinstance(exc, DocumentExtractionError) and str(exc) in _SAFE_EXTRACTION_ERRORS:
        return str(exc)
    return "analysis_failed"


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------


def _assert_can_analyze_case(actor: User, case: Case) -> None:
    """Judges always. Assistants only when they own the case."""
    if actor.role == UserRole.JUDGE and case.assigned_judge_id == actor.id:
        return
    if actor.role == UserRole.ASSISTANT and case.assistant_id == actor.id:
        return
    raise HTTPException(status_code=403, detail="forbidden")


def _assert_can_analyze_document(actor: User, doc: Document, case: Optional[Case]) -> None:
    """Judges can analyse any document. Assistants only their own uploads, or
    any doc attached to a case they own."""
    if actor.role == UserRole.JUDGE:
        return
    if doc.uploader_id == actor.id:
        return
    if case is not None and case.assistant_id == actor.id:
        return
    raise HTTPException(status_code=404, detail="document_not_found")


# ---------------------------------------------------------------------------
# Per-document
# ---------------------------------------------------------------------------


async def analyze_document(
    session: AsyncSession, *, actor: User, document_id: str
) -> AIAnalysis:
    """Run SudAI on a single document, persist the result, and log activity."""
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")

    case: Optional[Case] = None
    if doc.case_id is not None:
        case = await case_service.get_case_in_scope(session, doc.case_id, actor)
    _assert_can_analyze_document(actor, doc, case)

    # Seeded docs have empty storage paths → 410-style error. We treat
    # missing bytes as 404 here, mirroring the download endpoint.
    if not doc.storage_path:
        raise HTTPException(status_code=404, detail="file_missing")
    try:
        path = resolve_storage_path(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file_missing")
    if not path.exists():
        raise HTTPException(status_code=410, detail="seeded_file_no_bytes")

    settings = get_settings()
    analysis = AIAnalysis(
        case_id=doc.case_id,
        document_id=doc.id,
        requested_by_id=actor.id,
        status=AIAnalysisStatus.RUNNING,
        provider=settings.sudai_provider,
    )
    session.add(analysis)
    await session.flush()

    if case is not None:
        await activity_service.record_event(
            session,
            case_id=case.id,
            type=ActivityType.AI_DOCUMENT_ANALYSIS_REQUESTED,
            actor_id=actor.id,
            message_key="activity.ai_document_analysis_requested",
            meta={"documentId": doc.id, "fileName": doc.file_name},
        )

    try:
        result: AIAnalysisResponse = await pipeline_analyze_document(path, doc.file_name)
    except Exception as exc:  # noqa: BLE001 — client response stays generic
        _log.warning(
            "sudai_document_analysis_failed document_id=%s error_type=%s",
            doc.id,
            type(exc).__name__,
        )
        analysis.status = AIAnalysisStatus.FAILED
        analysis.error_message = _safe_analysis_error(exc)
        analysis.finished_at = datetime.utcnow()
        if case is not None:
            await activity_service.record_event(
                session,
                case_id=case.id,
                type=ActivityType.AI_DOCUMENT_ANALYSIS_FAILED,
                actor_id=actor.id,
                message_key="activity.ai_document_analysis_failed",
                meta={"documentId": doc.id, "error": analysis.error_message},
            )
        await session.flush()
        await session.commit()
        raise HTTPException(status_code=500, detail="ai_analysis_failed")

    analysis.result_json = result.model_dump(mode="json")
    analysis.status = AIAnalysisStatus.DONE
    analysis.finished_at = datetime.utcnow()

    if case is not None:
        await activity_service.record_event(
            session,
            case_id=case.id,
            type=ActivityType.AI_DOCUMENT_ANALYSIS_COMPLETED,
            actor_id=actor.id,
            message_key="activity.ai_document_analysis_completed",
            meta={
                "documentId": doc.id,
                "fileName": doc.file_name,
                "confidence": result.confidence_percent,
            },
        )
    await session.flush()
    return analysis


# ---------------------------------------------------------------------------
# Per-case (factual synthesis → retrieval → reasoning)
# ---------------------------------------------------------------------------


async def analyze_case_documents(
    session: AsyncSession, *, actor: User, case_id: str
) -> AIAnalysis:
    """Run the dedicated two-pass case pipeline over all attached documents.

    Permission mirrors per-document. Empty case (no docs) is a 400.
    """
    case = await case_service.get_case_in_scope(session, case_id, actor)
    _assert_can_analyze_case(actor, case)

    docs = await document_service.list_documents_for_case(session, actor=actor, case_id=case_id)
    if not docs:
        raise HTTPException(
            status_code=400,
            detail="no_documents:upload_at_least_one_document_to_analyze",
        )

    settings = get_settings()
    analysis = AIAnalysis(
        case_id=case.id,
        document_id=None,  # case-level run
        requested_by_id=actor.id,
        status=AIAnalysisStatus.RUNNING,
        provider=settings.sudai_provider,
    )
    session.add(analysis)
    await session.flush()

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.AI_CASE_ANALYSIS_REQUESTED,
        actor_id=actor.id,
        message_key="activity.ai_case_analysis_requested",
        meta={"documentCount": len(docs)},
    )

    sub_failures: list[dict[str, str]] = []
    sources: list[CaseDocumentSource] = []
    for doc in docs:
        if not doc.storage_path:
            sub_failures.append({"documentId": doc.id, "error": "file_missing"})
            continue
        try:
            path = resolve_storage_path(doc.storage_path)
        except FileNotFoundError:
            sub_failures.append({"documentId": doc.id, "error": "file_missing"})
            continue
        if not path.exists():
            sub_failures.append({"documentId": doc.id, "error": "seeded_file_no_bytes"})
            continue
        sources.append(
            CaseDocumentSource(
                document_id=doc.id,
                filename=doc.file_name,
                file_path=path,
            )
        )

    if not sources:
        analysis.status = AIAnalysisStatus.FAILED
        analysis.error_message = "all_documents_failed"
        analysis.finished_at = datetime.utcnow()
        await activity_service.record_event(
            session,
            case_id=case.id,
            type=ActivityType.AI_CASE_ANALYSIS_FAILED,
            actor_id=actor.id,
            message_key="activity.ai_case_analysis_failed",
            meta={"documentCount": len(docs), "failures": sub_failures},
        )
        await session.flush()
        await session.commit()
        raise HTTPException(status_code=500, detail="ai_analysis_failed:all_documents_failed")

    try:
        case_result = await pipeline_analyze_case_documents(sources)
    except Exception as exc:  # noqa: BLE001 — provider/extraction details stay server-side
        _log.warning(
            "sudai_case_analysis_failed case_id=%s error_type=%s",
            case.id,
            type(exc).__name__,
        )
        analysis.status = AIAnalysisStatus.FAILED
        analysis.error_message = _safe_analysis_error(exc)
        analysis.finished_at = datetime.utcnow()
        await activity_service.record_event(
            session,
            case_id=case.id,
            type=ActivityType.AI_CASE_ANALYSIS_FAILED,
            actor_id=actor.id,
            message_key="activity.ai_case_analysis_failed",
            meta={"documentCount": len(docs), "failures": sub_failures},
        )
        await session.flush()
        await session.commit()
        raise HTTPException(status_code=500, detail="ai_analysis_failed")

    sub_failures.extend(case_result.sub_failures)
    result = case_result.response
    payload = result.model_dump(mode="json")
    # Carry sub-failures through so the UI can warn about missing docs.
    if sub_failures:
        payload["sub_failures"] = sub_failures

    analysis.result_json = payload
    analysis.status = AIAnalysisStatus.DONE
    analysis.finished_at = datetime.utcnow()

    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.AI_CASE_ANALYSIS_COMPLETED,
        actor_id=actor.id,
        message_key="activity.ai_case_analysis_completed",
        meta={
            "documentCount": len(docs),
            "successfulCount": len(docs) - len(sub_failures),
            "failedCount": len(sub_failures),
            "confidence": result.confidence_percent,
        },
    )
    await session.flush()
    return analysis


# ---------------------------------------------------------------------------
# History / latest
# ---------------------------------------------------------------------------


def analysis_record_to_schema(row: AIAnalysis) -> AIAnalysisRecord:
    """Build the sole DB/internal → public analysis-record DTO boundary."""
    return AIAnalysisRecord(
        id=row.id,
        caseId=row.case_id,
        documentId=row.document_id,
        status=row.status.value if hasattr(row.status, "value") else str(row.status),
        provider=row.provider,
        startedAt=row.started_at,
        finishedAt=row.finished_at,
        errorMessage=row.error_message,
        result=analysis_result_to_api(row.result_json),
    )


async def list_analyses_for_case(
    session: AsyncSession, *, actor: User, case_id: str
) -> List[AIAnalysisRecord]:
    """Return only case-level analyses, newest first with a stable tie-break.

    Per-document records are available only through the document endpoint;
    otherwise a case panel can accidentally render a document result.
    """
    await case_service.get_case_in_scope(session, case_id, actor)
    res = await session.execute(
        select(AIAnalysis)
        .where(AIAnalysis.case_id == case_id, AIAnalysis.document_id.is_(None))
        .order_by(AIAnalysis.started_at.desc(), AIAnalysis.id.desc())
    )
    return [analysis_record_to_schema(r) for r in res.scalars().all()]


async def list_analyses_for_document(
    session: AsyncSession, *, actor: User, document_id: str
) -> List[AIAnalysisRecord]:
    """Return all analyses for a document, newest first. Permission check first."""
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    case: Optional[Case] = None
    if doc.case_id is not None:
        case = await case_service.get_case_in_scope(session, doc.case_id, actor)
    _assert_can_analyze_document(actor, doc, case)
    res = await session.execute(
        select(AIAnalysis)
        .where(AIAnalysis.document_id == document_id)
        .order_by(AIAnalysis.started_at.desc(), AIAnalysis.id.desc())
    )
    return [analysis_record_to_schema(r) for r in res.scalars().all()]


async def get_latest_for_case(
    session: AsyncSession, *, actor: User, case_id: str
) -> Optional[AIAnalysisRecord]:
    rows = await list_analyses_for_case(session, actor=actor, case_id=case_id)
    return rows[0] if rows else None


async def get_latest_for_document(
    session: AsyncSession, *, actor: User, document_id: str
) -> Optional[AIAnalysisRecord]:
    rows = await list_analyses_for_document(session, actor=actor, document_id=document_id)
    return rows[0] if rows else None
