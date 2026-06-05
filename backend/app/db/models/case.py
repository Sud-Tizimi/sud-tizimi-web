"""``cases`` table — case-management aggregate root."""
from __future__ import annotations

from sqlalchemy import Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin
from ...core.enums import CaseStatus


class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_status", "status"),
        Index("ix_cases_assigned_judge_id", "assigned_judge_id"),
        Index("ix_cases_assistant_id", "assistant_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    citizen_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, name="case_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=CaseStatus.DRAFT,
    )

    assigned_judge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assistant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Set when status == 'returned'. Carries the judge's reason.
    return_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
