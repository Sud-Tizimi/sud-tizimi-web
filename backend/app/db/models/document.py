"""``documents`` table — uploaded files (Phase B endpoints, table created in Phase A).

Per the user request, ``case_id`` is nullable: docs can be uploaded as
"orphan" via ``/upload`` and attached to a case later via
``POST /api/documents/{id}/attach`` (Phase B). Phase A only seeds the
table; endpoints come in Phase B.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ...core.enums import DocumentCategory, DocumentFileType, DocumentType


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_case_id", "case_id"),
        Index("ix_documents_uploader_id", "uploader_id"),
        Index("ix_documents_category", "category"),
        Index("ix_documents_detected_type", "detected_type"),
        Index("ix_documents_uploader_uploaded", "uploader_id", "uploaded_at"),
        # -1 = "pending classification", 0..100 = real confidence.
        CheckConstraint("ai_confidence >= -1 AND ai_confidence <= 100", name="ck_documents_ai_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploader_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[DocumentFileType] = mapped_column(
        SAEnum(
            DocumentFileType,
            name="document_file_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    category: Mapped[DocumentCategory] = mapped_column(
        SAEnum(
            DocumentCategory,
            name="document_category",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    detected_type: Mapped[DocumentType] = mapped_column(
        SAEnum(
            DocumentType,
            name="document_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    detected_type_label: Mapped[str] = mapped_column(String(128), nullable=False)
    ai_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
