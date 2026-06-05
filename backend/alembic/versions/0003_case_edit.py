"""add CASE_EDITED to activity_type enum

Revision ID: 0003_case_edit
Revises: 0002_seed
Create Date: 2026-06-05 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003_case_edit"
down_revision: Union[str, None] = "0002_seed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Match the value list from the original ``0001_initial.py`` so downgrade
# is symmetric with upgrade.
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
)
_ACTIVITY_VALUES_DOWNGRADE = tuple(v for v in _ACTIVITY_VALUES if v != "case_edited")


def upgrade() -> None:
    # MySQL stores ``sa.Enum(...)`` as a native ENUM column, so adding a
    # value means a full ``MODIFY COLUMN`` with the new value list. The
    # column is NOT NULL, so we don't need a default. If any row in
    # production ever held a value outside the new set, the ALTER would
    # fail — that's intentional.
    op.execute(
        "ALTER TABLE activity_events MODIFY COLUMN `type` "
        f"ENUM({', '.join(repr(v) for v in _ACTIVITY_VALUES)}) NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE activity_events MODIFY COLUMN `type` "
        f"ENUM({', '.join(repr(v) for v in _ACTIVITY_VALUES_DOWNGRADE)}) NOT NULL"
    )
