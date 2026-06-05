"""Documents router — upload, list, download, delete, attach, detach.

Phase B. Per-user data isolation is enforced in
``app.services.document_service``; this module is a thin HTTP wrapper.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.models.user import User
from .deps import get_current_user
from .schemas.document import (
    DocumentAttachRequest,
    DocumentListResponse,
    DocumentResponse,
)
from ..services import document_service

log = logging.getLogger("api.documents")

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload(
    file: UploadFile = File(..., description="PDF / DOCX / JPG / PNG, up to 25 MB"),
    case_id: Optional[str] = Form(default=None, alias="caseId"),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a document. ``caseId`` is optional; when omitted, the document
    is stored as an orphan and surfaced under ``/documents?scope=mine``.
    """
    doc = await document_service.upload_document(
        session, actor=user, file=file, case_id=case_id
    )
    await session.commit()
    shaped = (await document_service.shape_for_response(session, [doc]))[0]
    return DocumentResponse.model_validate(shaped)


@router.get("", response_model=DocumentListResponse)
async def list_mine(
    scope: str = Query(default="mine", pattern="^(mine|all)$"),
    case_id: Optional[str] = Query(default=None, alias="caseId"),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """List documents. ``scope=mine`` (default) returns only the current
    user's uploads; ``scope=all`` returns every document (judges only).
    Optionally pass ``caseId=…`` to scope to one case.
    """
    docs = await document_service.list_documents(
        session, actor=user, scope=scope, case_id=case_id
    )
    shaped = await document_service.shape_for_response(session, docs)
    return DocumentListResponse(documents=[DocumentResponse.model_validate(d) for d in shaped])


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_one(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    from ..db.models.document import Document
    doc = await session.get(Document, document_id)
    if doc is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="document_not_found")
    if user.role.value != "judge" and doc.uploader_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="document_not_found")
    shaped = (await document_service.shape_for_response(session, [doc]))[0]
    return DocumentResponse.model_validate(shaped)


@router.get("/{document_id}/download")
async def download(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream the raw file. Returns 410 for seeded files that have no
    on-disk bytes (Phase A seed doesn't write real files).
    """
    doc, path = await document_service.get_document_for_download(
        session, actor=user, document_id=document_id
    )
    return FileResponse(
        path=str(path),
        media_type=_content_type_for(doc.file_type),
        filename=doc.file_name,
    )


@router.delete("/{document_id}", status_code=204, response_class=Response)
async def delete_one(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    await document_service.delete_document(
        session, actor=user, document_id=document_id
    )
    await session.commit()
    return Response(status_code=204)


@router.post("/{document_id}/attach", response_model=DocumentResponse)
async def attach(
    document_id: str,
    payload: DocumentAttachRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = await document_service.attach_document(
        session, actor=user, document_id=document_id, case_id=payload.case_id
    )
    await session.commit()
    shaped = (await document_service.shape_for_response(session, [doc]))[0]
    return DocumentResponse.model_validate(shaped)


@router.post("/{document_id}/detach", response_model=DocumentResponse)
async def detach(
    document_id: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    doc = await document_service.detach_document(
        session, actor=user, document_id=document_id
    )
    await session.commit()
    shaped = (await document_service.shape_for_response(session, [doc]))[0]
    return DocumentResponse.model_validate(shaped)


def _content_type_for(file_type) -> str:
    value = file_type.value if hasattr(file_type, "value") else file_type
    if value == "pdf":
        return "application/pdf"
    if value == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if value == "jpg":
        return "image/jpeg"
    if value == "png":
        return "image/png"
    return "application/octet-stream"
