"""add split_breakdown to bills

Revision ID: b2e5d8f3c6a1
Revises: a1f4c7e9b2d5
Create Date: 2026-07-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2e5d8f3c6a1"
down_revision: str | None = "a1f4c7e9b2d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bills",
        sa.Column("split_breakdown", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bills", "split_breakdown")
