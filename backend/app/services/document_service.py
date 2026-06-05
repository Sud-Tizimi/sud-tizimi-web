"""Document service — upload, list, download, delete, attach, detach.

Per-user data isolation:
  * ``list_documents`` defaults to ``scope='mine'`` (uploader_id == me). A
    judge can pass ``scope='all'`` to see every document in the system.
  * ``download_document`` allows the uploader + any judge.
  * ``delete_document`` allows the uploader + any judge.
  * ``attach_document`` and ``detach_document`` allow the uploader + any
    judge, and require the case to be visible to the actor.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.enums import (
    ActivityType,
    DocumentCategory,
    DocumentFileType,
    NotificationKind,
    UserRole,
)
from ..core.ids import gen_document_id
from ..core.storage import (
    build_storage_path,
    delete_file_silently,
    ensure_storage_root,
    relative_to_root,
    resolve_storage_path,
)
from ..db.models.case import Case
from ..db.models.document import Document
from ..db.models.user import User
from . import activity_service, case_service, classification_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _file_type_for_name(name: str) -> Optional[DocumentFileType]:
    ext = name.lower().split(".")[-1] if "." in name else ""
    if ext == "pdf":
        return DocumentFileType.PDF
    if ext == "docx":
        return DocumentFileType.DOCX
    if ext in ("jpg", "jpeg"):
        return DocumentFileType.JPG
    if ext == "png":
        return DocumentFileType.PNG
    return None


async def _read_into_storage(
    file: UploadFile, dest: Path, max_bytes: int
) -> int:
    """Stream the upload to disk, enforcing ``max_bytes``.

    Raises 413 if the file exceeds the cap. Returns the byte count written.
    """
    ensure_storage_root()
    written = 0
    chunk_size = 64 * 1024
    async with aiofiles.open(dest, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                await f.close()
                delete_file_silently(dest)
                raise HTTPException(
                    status_code=413,
                    detail=f"audio_too_large:max_{max_bytes}_bytes",
                )
    return written


def _public(doc: Document, uploader_name: str = "") -> dict:
    """Shape a Document ORM row into the camelCase JSON response."""
    return {
        "id": doc.id,
        "caseId": doc.case_id,
        "uploaderId": doc.uploader_id,
        "uploaderName": uploader_name,
        "fileName": doc.file_name,
        "fileType": doc.file_type.value if hasattr(doc.file_type, "value") else doc.file_type,
        "size": doc.size_bytes,
        "category": doc.category.value if hasattr(doc.category, "value") else doc.category,
        "detectedType": doc.detected_type.value if hasattr(doc.detected_type, "value") else doc.detected_type,
        "detectedTypeLabel": doc.detected_type_label,
        "aiConfidence": doc.ai_confidence,
        "uploadedAt": doc.uploaded_at,
    }


async def _uploader_name(session: AsyncSession, uploader_id: str) -> str:
    user = await session.get(User, uploader_id)
    return user.full_name if user else ""


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

async def upload_document(
    session: AsyncSession,
    *,
    actor: User,
    file: UploadFile,
    case_id: Optional[str] = None,
) -> Document:
    """Upload a single file. Returns the persisted Document.

    The case is optional: when ``case_id`` is None the document is created
    as an orphan and surfaces in ``/api/documents?scope=mine`` with
    ``caseId=null``. The client can later attach it via
    ``POST /api/documents/{id}/attach``.
    """
    settings = get_settings()
    allowed_exts = settings.allowed_upload_extensions_tuple
    max_bytes = settings.max_upload_bytes

    if not file.filename:
        raise HTTPException(status_code=400, detail="empty_filename")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported_extension:{ext}",
        )
    file_type = _file_type_for_name(file.filename)
    if file_type is None:
        raise HTTPException(status_code=400, detail="unsupported_extension")

    if case_id is not None:
        # Scope check: the case must be in the actor's scope.
        case = await case_service.get_case_in_scope(session, case_id, actor)
        if case.assigned_judge_id != actor.id and case.assistant_id != actor.id:
            raise HTTPException(status_code=403, detail="forbidden")

    # Classify before persisting so the row is fully populated.
    classification = classification_service.classify(file.filename, file_type)

    doc_id = gen_document_id()
    dest = build_storage_path(actor.id, doc_id, ext)
    written = await _read_into_storage(file, dest, max_bytes)

    doc = Document(
        id=doc_id,
        case_id=case_id,
        uploader_id=actor.id,
        file_name=file.filename,
        file_type=file_type,
        size_bytes=written,
        storage_path=relative_to_root(dest),
        category=classification.category,
        detected_type=classification.detected_type,
        detected_type_label=classification.detected_type_label,
        ai_confidence=classification.ai_confidence,
        uploaded_at=datetime.utcnow(),
    )
    session.add(doc)
    await session.flush()

    # Side effects: activity event in the case (if attached), and an
    # automatic draft → uploaded transition when the case is empty.
    if case_id is not None:
        await activity_service.record_event(
            session,
            case_id=case_id,
            type=ActivityType.DOCUMENT_ADDED,
            actor_id=actor.id,
            message_key="activity.document_added",
            meta={"fileName": file.filename, "size": written},
        )
        # If the case is still draft and has at least one doc, mark it uploaded.
        case = await session.get(Case, case_id)
        if case is not None and case.status.value == "draft":
            case.status = type(case.status).UPLOADED
            case.updated_at = datetime.utcnow()
            await session.flush()
            await activity_service.record_event(
                session,
                case_id=case_id,
                type=ActivityType.DOCUMENTS_UPLOADED,
                actor_id=actor.id,
                message_key="activity.documents_uploaded",
                meta={"count": 1},
            )

    return doc


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def list_documents(
    session: AsyncSession,
    *,
    actor: User,
    scope: str = "mine",
    case_id: Optional[str] = None,
) -> list[Document]:
    """Return documents visible to ``actor``.

    - ``scope='mine'``  → only the actor's uploads.
    - ``scope='all'``   → every document (judges only; assistants 403).
    - ``case_id='…'``   → only docs attached to that case (still scoped).
    """
    stmt = select(Document)
    if case_id is not None:
        # Scope check the case first.
        case = await case_service.get_case_in_scope(session, case_id, actor)
        stmt = stmt.where(Document.case_id == case_id)
    elif scope == "all":
        if actor.role != UserRole.JUDGE:
            raise HTTPException(status_code=403, detail="forbidden")
    else:
        # Default: only the actor's uploads.
        stmt = stmt.where(Document.uploader_id == actor.id)
    stmt = stmt.order_by(Document.uploaded_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def list_documents_for_case(
    session: AsyncSession, *, actor: User, case_id: str
) -> list[Document]:
    """All docs attached to a case, after the scope check."""
    await case_service.get_case_in_scope(session, case_id, actor)
    res = await session.execute(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.uploaded_at.asc())
    )
    return list(res.scalars().all())


# ---------------------------------------------------------------------------
# Single
# ---------------------------------------------------------------------------

async def _assert_can_modify(
    session: AsyncSession, actor: User, doc: Document
) -> None:
    """Uploader can do anything with their own doc. Judges can do anything
    with any doc (oversight). Assistants cannot touch other assistants' docs.
    """
    if actor.role == UserRole.JUDGE:
        return
    if doc.uploader_id == actor.id:
        return
    raise HTTPException(status_code=403, detail="forbidden")


async def get_document_for_download(
    session: AsyncSession, *, actor: User, document_id: str
) -> tuple[Document, Path]:
    """Resolve a document to its on-disk path after a permission check."""
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    if actor.role != UserRole.JUDGE and doc.uploader_id != actor.id:
        raise HTTPException(status_code=404, detail="document_not_found")
    try:
        path = resolve_storage_path(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file_missing")
    if not path.exists():
        # Seeded files don't have real on-disk bytes. Surface a 410 to
        # distinguish from a permission error.
        raise HTTPException(status_code=410, detail="seeded_file_no_bytes")
    return doc, path


async def delete_document(
    session: AsyncSession, *, actor: User, document_id: str
) -> None:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    await _assert_can_modify(session, actor, doc)
    try:
        path = resolve_storage_path(doc.storage_path)
        delete_file_silently(path)
    except FileNotFoundError:
        pass
    # Capture audit fields before the row is gone.
    case_id = doc.case_id
    file_name = doc.file_name
    await session.delete(doc)
    await session.flush()
    if case_id:
        await activity_service.record_event(
            session,
            case_id=case_id,
            type=ActivityType.DOCUMENT_REMOVED,
            actor_id=actor.id,
            message_key="activity.document_removed",
            meta={"fileName": file_name},
        )


# ---------------------------------------------------------------------------
# Attach / detach
# ---------------------------------------------------------------------------

async def attach_document(
    session: AsyncSession, *, actor: User, document_id: str, case_id: str
) -> Document:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    await _assert_can_modify(session, actor, doc)
    case = await case_service.get_case_in_scope(session, case_id, actor)
    if case.assigned_judge_id != actor.id and case.assistant_id != actor.id:
        raise HTTPException(status_code=403, detail="forbidden")
    doc.case_id = case.id
    case.updated_at = datetime.utcnow()
    await session.flush()
    await activity_service.record_event(
        session,
        case_id=case.id,
        type=ActivityType.DOCUMENT_ADDED,
        actor_id=actor.id,
        message_key="activity.document_added",
        meta={"fileName": doc.file_name, "attached": True},
    )
    return doc


async def detach_document(
    session: AsyncSession, *, actor: User, document_id: str
) -> Document:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    await _assert_can_modify(session, actor, doc)
    if doc.case_id is None:
        # Already orphan.
        return doc
    case_id = doc.case_id
    file_name = doc.file_name
    doc.case_id = None
    await session.flush()
    await activity_service.record_event(
        session,
        case_id=case_id,
        type=ActivityType.DOCUMENT_REMOVED,
        actor_id=actor.id,
        message_key="activity.document_removed",
        meta={"fileName": file_name, "detached": True},
    )
    return doc


async def shape_for_response(
    session: AsyncSession, docs: Sequence[Document]
) -> list[dict]:
    """Resolve uploader display names in one query, then return public dicts."""
    if not docs:
        return []
    uploader_ids = {d.uploader_id for d in docs}
    res = await session.execute(
        select(User.id, User.full_name).where(User.id.in_(uploader_ids))
    )
    name_by_id = {row[0]: row[1] for row in res.all()}
    return [_public(d, name_by_id.get(d.uploader_id, "")) for d in docs]
