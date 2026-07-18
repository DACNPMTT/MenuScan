"""add menu host selections

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-18 03:00:00.000000

Persists the menu owner's own dish picks (the host's order draft) so they survive
a reload and show up next to the guests' picks, instead of living only in the
browser until a bill is exported.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "menu_host_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("menu_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_menu_host_selections_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["menu_id"],
            ["menus.id"],
            name="fk_menu_host_selections_menu_id_menus",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"],
            ["food_items.id"],
            name="fk_menu_host_selections_food_item_id_food_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_menu_host_selections"),
        sa.UniqueConstraint(
            "menu_id",
            "food_item_id",
            name="uq_menu_host_selections_menu_item",
        ),
    )
    op.create_index(
        "ix_menu_host_selections_menu_id",
        "menu_host_selections",
        ["menu_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_menu_host_selections_menu_id", table_name="menu_host_selections"
    )
    op.drop_table("menu_host_selections")
