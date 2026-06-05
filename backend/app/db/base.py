"""SQLAlchemy 2.0 declarative base for the Sud-Tizimi ORM."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """All ORM models inherit from this base."""


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns with UTC defaults.

    MySQL does not auto-update ``updated_at`` unless the column is declared
    with ``ON UPDATE CURRENT_TIMESTAMP``. We rely on application-level
    ``onupdate=func.now()`` so the same code works in tests (sqlite) and
    production (mysql).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
