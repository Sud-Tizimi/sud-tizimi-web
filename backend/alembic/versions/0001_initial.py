"""initial: users, cases, documents, activity_events, notifications

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-04 23:50:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("judge", "assistant", name="user_role"),
            nullable=False,
        ),
        sa.Column("court", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # ------------------------------------------------------------------
    # cases
    # ------------------------------------------------------------------
    op.create_table(
        "cases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("case_number", sa.String(length=64), nullable=False, unique=True),
        sa.Column("citizen_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "uploaded", "under_review", "approved", "returned",
                name="case_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("assigned_judge_id", sa.String(length=36), nullable=False),
        sa.Column("assistant_id", sa.String(length=36), nullable=False),
        sa.Column("return_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["assigned_judge_id"], ["users.id"], name="fk_cases_judge", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assistant_id"], ["users.id"], name="fk_cases_assistant", ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_assigned_judge_id", "cases", ["assigned_judge_id"])
    op.create_index("ix_cases_assistant_id", "cases", ["assistant_id"])

    # ------------------------------------------------------------------
    # documents (table only — endpoints come in Phase B)
    # ------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), nullable=True),
        sa.Column("uploader_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column(
            "file_type",
            sa.Enum("pdf", "docx", "jpg", "png", name="document_file_type"),
            nullable=False,
        ),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "procedural", "participant", "evidence", "court",
                name="document_category",
            ),
            nullable=False,
        ),
        sa.Column(
            "detected_type",
            sa.Enum(
                "claim", "counterclaim", "appeal", "cassation_appeal", "statement",
                "explanation", "objection", "additional_statement",
                "contract", "financial_document", "personal_document",
                "court_decision", "court_resolution", "hearing_transcript",
                name="document_type",
            ),
            nullable=False,
        ),
        sa.Column("detected_type_label", sa.String(length=128), nullable=False),
        sa.Column("ai_confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "ai_confidence >= -1 AND ai_confidence <= 100",
            name="ck_documents_ai_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name="fk_documents_case", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["uploader_id"], ["users.id"], name="fk_documents_uploader", ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_uploader_id", "documents", ["uploader_id"])
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_detected_type", "documents", ["detected_type"])
    op.create_index("ix_documents_uploader_uploaded", "documents", ["uploader_id", "uploaded_at"])

    # ------------------------------------------------------------------
    # activity_events
    # ------------------------------------------------------------------
    op.create_table(
        "activity_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "case_created", "documents_uploaded", "documents_classified",
                "case_submitted", "case_approved", "case_returned",
                "document_added", "document_removed",
                name="activity_type",
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("message_key", sa.String(length=128), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name="fk_activity_case", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_activity_actor", ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_activity_case_id_at", "activity_events", ["case_id", "at"])

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("recipient_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "case_submitted_to_judge",
                "case_returned_to_assistant",
                "case_approved",
                name="notification_kind",
            ),
            nullable=False,
        ),
        sa.Column("message_key", sa.String(length=128), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["recipient_id"], ["users.id"], name="fk_notifications_recipient", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name="fk_notifications_case", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_notifications_recipient_at", "notifications", ["recipient_id", "at"])
    op.create_index("ix_notifications_recipient_read", "notifications", ["recipient_id", "read"])


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_read", table_name="notifications")
    op.drop_index("ix_notifications_recipient_at", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_activity_case_id_at", table_name="activity_events")
    op.drop_table("activity_events")

    op.drop_index("ix_documents_uploader_uploaded", table_name="documents")
    op.drop_index("ix_documents_detected_type", table_name="documents")
    op.drop_index("ix_documents_category", table_name="documents")
    op.drop_index("ix_documents_uploader_id", table_name="documents")
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_cases_assistant_id", table_name="cases")
    op.drop_index("ix_cases_assigned_judge_id", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_table("cases")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")
