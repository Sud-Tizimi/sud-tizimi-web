"""Case CRUD + workflow router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.models.user import User
from ..services import case_service, document_service
from .deps import get_current_user
from .schemas.case import (
    CaseCreateRequest,
    CaseListResponse,
    CaseResponse,
    CaseReturnRequest,
    StatusTransitionResponse,
)
from .schemas.document import DocumentListResponse, DocumentResponse

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=CaseListResponse)
async def list_my_cases(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseListResponse:
    cases = await case_service.list_cases_for_user(session, user)
    return CaseListResponse(cases=[CaseResponse.model_validate(c) for c in cases])


@router.get("/{case_id}", response_model=CaseResponse)
async def get_one(
    case_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseResponse:
    case = await case_service.get_case_in_scope(session, case_id, user)
    return CaseResponse.model_validate(case)


@router.post("", response_model=CaseResponse, status_code=201)
async def create_one(
    payload: CaseCreateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseResponse:
    case = await case_service.create_case(
        session,
        actor=user,
        case_number=payload.case_number,
        citizen_name=payload.citizen_name,
        description=payload.description,
        assigned_judge_id=payload.assigned_judge_id,
    )
    await session.commit()
    return CaseResponse.model_validate(case)


@router.post("/{case_id}/submit", response_model=StatusTransitionResponse)
async def submit(
    case_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatusTransitionResponse:
    case = await case_service.submit_case(session, case_id=case_id, actor=user)
    await session.commit()
    return StatusTransitionResponse(case=CaseResponse.model_validate(case))


@router.post("/{case_id}/approve", response_model=StatusTransitionResponse)
async def approve(
    case_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatusTransitionResponse:
    case = await case_service.approve_case(session, case_id=case_id, actor=user)
    await session.commit()
    return StatusTransitionResponse(case=CaseResponse.model_validate(case))


@router.post("/{case_id}/return", response_model=StatusTransitionResponse)
async def return_one(
    case_id: str,
    payload: CaseReturnRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatusTransitionResponse:
    case = await case_service.return_case(
        session, case_id=case_id, actor=user, reason=payload.reason
    )
    await session.commit()
    return StatusTransitionResponse(case=CaseResponse.model_validate(case))


@router.post("/{case_id}/reopen", response_model=StatusTransitionResponse)
async def reopen(
    case_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatusTransitionResponse:
    """Reserved for Phase B UI. No-op on notifications, no activity row."""
    case = await case_service.reopen_case(session, case_id=case_id, actor=user)
    await session.commit()
    return StatusTransitionResponse(case=CaseResponse.model_validate(case))


# ---------------------------------------------------------------------------
# Documents nested under a case
# ---------------------------------------------------------------------------

@router.get("/{case_id}/documents", response_model=DocumentListResponse)
async def list_case_documents(
    case_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentListResponse:
    docs = await document_service.list_documents_for_case(
        session, actor=user, case_id=case_id
    )
    shaped = await document_service.shape_for_response(session, docs)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in shaped]
    )


@router.post(
    "/{case_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_case_document(
    case_id: str,
    file: UploadFile = File(..., description="PDF / DOCX / JPG / PNG, up to 25 MB"),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a document and attach it to this case in one step. The
    per-case scope check runs inside ``upload_document``.
    """
    doc = await document_service.upload_document(
        session, actor=user, file=file, case_id=case_id
    )
    await session.commit()
    shaped = (await document_service.shape_for_response(session, [doc]))[0]
    return DocumentResponse.model_validate(shaped)
