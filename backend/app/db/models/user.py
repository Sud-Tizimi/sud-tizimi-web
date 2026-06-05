"""``users`` table — accounts with a role."""
from __future__ import annotations

from sqlalchemy import Enum as SAEnum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin
from ...core.enums import UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role", "role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    # ``court`` is only meaningful for judges; for assistants we leave it NULL.
    court: Mapped[str | None] = mapped_column(String(255), nullable=True)
