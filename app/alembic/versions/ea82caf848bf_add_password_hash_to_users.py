"""add_password_hash_to_users

Revision ID: ea82caf848bf
Revises: 001
Create Date: 2026-06-25 06:02:05.611949
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "ea82caf848bf"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
