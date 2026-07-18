"""link menus to a dining session (multi-meal)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-18 02:30:00.000000

A dining session can now span several meals: every scanned menu points back at
its session via menus.dining_session_id (many menus -> one session). Existing
single-meal sessions are backfilled from the old dining_sessions.menu_id pointer
so their one meal shows up in the new meals list.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "menus",
        sa.Column("dining_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_menus_dining_session_id_dining_sessions",
        "menus",
        "dining_sessions",
        ["dining_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_menus_dining_session_id", "menus", ["dining_session_id"])

    # Backfill: each existing session's single menu becomes its first meal.
    op.execute(
        """
        UPDATE menus
        SET dining_session_id = ds.id
        FROM dining_sessions ds
        WHERE ds.menu_id = menus.id
          AND menus.dining_session_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_menus_dining_session_id", table_name="menus")
    op.drop_constraint(
        "fk_menus_dining_session_id_dining_sessions", "menus", type_="foreignkey"
    )
    op.drop_column("menus", "dining_session_id")
