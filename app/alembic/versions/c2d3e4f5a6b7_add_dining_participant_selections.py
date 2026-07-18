"""add dining participant selections

Revision ID: c2d3e4f5a6b7
Revises: a1b2c3d4e5f7
Create Date: 2026-07-18 00:00:00.000000

Adds the table that stores which dishes each guest picked in a group dining
session (quantity + note), so the host can see who ordered what and split the
bill per person.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dining_session_participant_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            name="ck_dining_session_participant_selections_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["dining_session_participants.id"],
            name="fk_dining_participant_selections_participant_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"],
            ["food_items.id"],
            name="fk_dining_participant_selections_food_item_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_dining_session_participant_selections",
        ),
        sa.UniqueConstraint(
            "participant_id",
            "food_item_id",
            name="uq_dining_participant_selections_participant_item",
        ),
    )
    op.create_index(
        "ix_dining_session_participant_selections_participant_id",
        "dining_session_participant_selections",
        ["participant_id"],
    )
    op.create_index(
        "ix_dining_session_participant_selections_food_item_id",
        "dining_session_participant_selections",
        ["food_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dining_session_participant_selections_food_item_id",
        table_name="dining_session_participant_selections",
    )
    op.drop_index(
        "ix_dining_session_participant_selections_participant_id",
        table_name="dining_session_participant_selections",
    )
    op.drop_table("dining_session_participant_selections")
