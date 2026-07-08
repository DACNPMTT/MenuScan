"""add menu status and soft delete

Revision ID: f32b7c1a9e6d
Revises: b1fe7f837a7c
Create Date: 2026-07-02 08:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f32b7c1a9e6d"
down_revision: str | None = "b1fe7f837a7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    menu_status = postgresql.ENUM("DRAFT", "CONFIRMED", name="menu_status")
    menu_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "menus",
        sa.Column(
            "status",
            sa.Enum("DRAFT", "CONFIRMED", name="menu_status"),
            server_default="DRAFT",
            nullable=False,
        ),
    )
    op.add_column(
        "menus",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_menus_deleted_at", "menus", ["deleted_at"])
    op.create_index("ix_menus_updated_at", "menus", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_menus_updated_at", table_name="menus")
    op.drop_index("ix_menus_deleted_at", table_name="menus")
    op.drop_column("menus", "deleted_at")
    op.drop_column("menus", "status")
    postgresql.ENUM(name="menu_status").drop(op.get_bind(), checkfirst=True)
