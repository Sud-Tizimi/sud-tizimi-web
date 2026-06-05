"""``ai_analyses`` table — SudAI-Law-UZ analysis history.

Each row is one analysis run. Per-document runs have a non-null
``document_id``; case-level aggregated runs have a null ``document_id``.

The full result payload (``AIAnalysisResponse``) is stored as JSON in
``result_json`` — convenient to ship to the frontend in one query, and
we keep history so users can re-run analysis and compare runs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ...core.enums import AIAnalysisStatus
from ...core.ids import gen_ai_analysis_id


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        Index("ix_ai_analyses_case_id_started_at", "case_id", "started_at"),
        Index("ix_ai_analyses_document_id", "document_id"),
        Index("ix_ai_analyses_requested_by_started_at", "requested_by_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=gen_ai_analysis_id
    )
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    # NULL for case-level aggregated runs.
    document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    requested_by_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[AIAnalysisStatus] = mapped_column(
        SAEnum(
            AIAnalysisStatus,
            name="ai_analysis_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=AIAnalysisStatus.PENDING,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
