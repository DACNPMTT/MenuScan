"""add ai_throttle table (anti-spam throttle for AI calls)

Revision ID: f1a2b3c4d5e6
Revises: 8a9b0c1d2e3f
Create Date: 2026-07-11 21:00:00.000000

One row per (subject, action) holding the last AI-call timestamp, used to
enforce a minimum gap between calls (scan, chat). Not a daily quota.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "8a9b0c1d2e3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_throttle",
        sa.Column("subject_type", sa.String(length=8), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column(
            "last_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "subject_type",
            "subject_id",
            "action",
            name="pk_ai_throttle",
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_throttle")
