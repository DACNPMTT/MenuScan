"""make_user_sessions_user_id_not_null

Revision ID: d7e9f3b1a8c4
Revises: ccfae21342e0
Create Date: 2026-07-01 03:50:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd7e9f3b1a8c4'
down_revision: str | None = 'ccfae21342e0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM user_sessions WHERE user_id IS NULL"))
    op.alter_column(
        'user_sessions',
        'user_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        'user_sessions',
        'user_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True
    )
