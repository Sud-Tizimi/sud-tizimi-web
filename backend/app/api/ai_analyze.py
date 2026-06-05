"""SudAI-Law-UZ HTTP router.

Thin wrapper around :mod:`app.services.ai_analyze_service`. Four
endpoints:

* ``POST /api/cases/{case_id}/analysis``       — run on all case documents
* ``GET  /api/cases/{case_id}/analysis``       — list history (case scope)
* ``POST /api/documents/{document_id}/analysis`` — run on a single document
* ``GET  /api/documents/{document_id}/analysis`` — list history (doc scope)

All endpoints require a valid JWT (``get_current_user``).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.models.user import User
from ..services import ai_analyze_service
from .deps import get_current_user
from .schemas.ai_analysis import (
    AIAnalysisRecord,
    AIAnalysisRecordList,
    AICaseAnalysisRequest,
    AIDocumentAnalysisRequest,
)

# Case-scoped router — mounted at /api
case_router = APIRouter(prefix="/cases/{case_id}/analysis", tags=["ai-analysis"])


@case_router.post("", response_model=AIAnalysisRecord)
async def trigger_case_analysis(
    case_id: str,
    payload: AICaseAnalysisRequest | None = None,  # noqa: ARG001 — trigger body, currently empty
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIAnalysisRecord:
    analysis = await ai_analyze_service.analyze_case_documents(
        session, actor=user, case_id=case_id
    )
    await session.commit()
    # Re-fetch via list to honour the response shape consistently.
    records = await ai_analyze_service.list_analyses_for_case(
        session, actor=user, case_id=case_id
    )
    return records[0] if records else _to_record(analysis)


@case_router.get("", response_model=AIAnalysisRecordList)
async def list_case_analyses(
    case_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIAnalysisRecordList:
    records = await ai_analyze_service.list_analyses_for_case(
        session, actor=user, case_id=case_id
    )
    return AIAnalysisRecordList(records=records)


# Document-scoped router — mounted at /api
doc_router = APIRouter(prefix="/documents/{document_id}/analysis", tags=["ai-analysis"])


@doc_router.post("", response_model=AIAnalysisRecord)
async def trigger_document_analysis(
    document_id: str,
    payload: AIDocumentAnalysisRequest | None = None,  # noqa: ARG001
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIAnalysisRecord:
    analysis = await ai_analyze_service.analyze_document(
        session, actor=user, document_id=document_id
    )
    await session.commit()
    records = await ai_analyze_service.list_analyses_for_document(
        session, actor=user, document_id=document_id
    )
    return records[0] if records else _to_record(analysis)


@doc_router.get("", response_model=AIAnalysisRecordList)
async def list_document_analyses(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIAnalysisRecordList:
    records = await ai_analyze_service.list_analyses_for_document(
        session, actor=user, document_id=document_id
    )
    return AIAnalysisRecordList(records=records)


# Backwards-compat alias for any consumer that imports the old ``router`` name.
router = case_router


def _to_record(analysis) -> AIAnalysisRecord:
    """Convert an in-memory :class:`AIAnalysis` ORM row to the API record.

    Used only as a fallback when the post-commit re-list returns empty
    (should not happen in practice — defence in depth).
    """
    return AIAnalysisRecord(
        id=analysis.id,
        caseId=analysis.case_id,
        documentId=analysis.document_id,
        status=analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status),
        provider=analysis.provider,
        startedAt=analysis.started_at,
        finishedAt=analysis.finished_at,
        errorMessage=analysis.error_message,
        result=analysis.result_json,
    )
