"""add ai_analyses table + extend activity_type enum (Phase 27: SudAI)

Revision ID: 0004_ai_analyses
Revises: 0003_case_edit
Create Date: 2026-06-05 12:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0004_ai_analyses"
down_revision: Union[str, None] = "0003_case_edit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Extended activity_type values (Phase 27 adds six SudAI events).
_ACTIVITY_VALUES = (
    "case_created",
    "case_edited",
    "documents_uploaded",
    "documents_classified",
    "case_submitted",
    "case_approved",
    "case_returned",
    "document_added",
    "document_removed",
    "ai_document_analysis_requested",
    "ai_document_analysis_completed",
    "ai_document_analysis_failed",
    "ai_case_analysis_requested",
    "ai_case_analysis_completed",
    "ai_case_analysis_failed",
)
_ACTIVITY_VALUES_DOWNGRADE = tuple(
    v
    for v in _ACTIVITY_VALUES
    if not v.startswith("ai_")
)


# ai_analysis_status enum values (mirror app.core.enums.AIAnalysisStatus).
_AI_STATUS_VALUES = ("pending", "running", "done", "failed")


def upgrade() -> None:
    # 1. Extend activity_type enum.
    op.execute(
        "ALTER TABLE activity_events MODIFY COLUMN `type` "
        f"ENUM({', '.join(repr(v) for v in _ACTIVITY_VALUES)}) NOT NULL"
    )

    # 2. Create ai_analyses table. Mirrors db/models/ai_analysis.py.
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "requested_by_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(*_AI_STATUS_VALUES, name="ai_analysis_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("result_json", sa.JSON, nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index(
        "ix_ai_analyses_case_id_started_at",
        "ai_analyses",
        ["case_id", "started_at"],
    )
    op.create_index(
        "ix_ai_analyses_document_id",
        "ai_analyses",
        ["document_id"],
    )
    op.create_index(
        "ix_ai_analyses_requested_by_started_at",
        "ai_analyses",
        ["requested_by_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_analyses_requested_by_started_at", table_name="ai_analyses")
    op.drop_index("ix_ai_analyses_document_id", table_name="ai_analyses")
    op.drop_index("ix_ai_analyses_case_id_started_at", table_name="ai_analyses")
    op.drop_table("ai_analyses")

    op.execute(
        "ALTER TABLE activity_events MODIFY COLUMN `type` "
        f"ENUM({', '.join(repr(v) for v in _ACTIVITY_VALUES_DOWNGRADE)}) NOT NULL"
    )
