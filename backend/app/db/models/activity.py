"""``activity_events`` table — per-case timeline (case-management.md §11)."""
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
from ...core.enums import ActivityType


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_case_id_at", "case_id", "at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ActivityType] = mapped_column(
        SAEnum(
            ActivityType,
            name="activity_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Translation key consumed by the frontend i18n.
    message_key: Mapped[str] = mapped_column(String(128), nullable=False)
    # Optional interpolation bag for the translation key.
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
