"""``notifications`` table — in-system notifications (case-management.md §17)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base
from ...core.enums import NotificationKind


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_at", "recipient_id", "at"),
        Index("ix_notifications_recipient_read", "recipient_id", "read"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    recipient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[NotificationKind] = mapped_column(
        SAEnum(
            NotificationKind,
            name="notification_kind",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    message_key: Mapped[str] = mapped_column(String(128), nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
