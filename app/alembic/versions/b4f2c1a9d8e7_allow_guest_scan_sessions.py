"""allow_guest_scan_sessions

Revision ID: b4f2c1a9d8e7
Revises: 7f1c6c9d2a4b
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b4f2c1a9d8e7"
down_revision: str | None = "7f1c6c9d2a4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "scan_sessions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM scan_sessions WHERE user_id IS NULL"))
    op.alter_column(
        "scan_sessions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
