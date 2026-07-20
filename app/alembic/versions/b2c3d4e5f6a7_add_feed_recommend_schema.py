"""add feed_recommend schema

Revision ID: b2c3d4e5f6a7
Revises: a1f4c7e9b2d5
Create Date: 2026-07-19 00:00:00.000000

Adds the persistence layer for the rule-based restaurant "Discovery" feed:
- ``user_locations``: 1:1 per-user lat/lng + free-text address + source.
- ``user_restaurant_saves``: bookmarked restaurants (per user, by
  ``restaurant_source_id``).
- ``user_restaurant_seen``: skip/view log so the feed does not resurface
  restaurants the diner has already passed on.
- ``users.price_band_cents``: comfortable average price (VND) used by the
  price-fit scoring term; NULL disables the term.
- ``dining_sessions.restaurant_source_id``: optional metadata so a saved
  card can become a group dining session ("the place we agreed on").

The restaurant dataset itself is NOT a database table — it lives in
``data/restaurants.json`` and is read into an in-memory cache by
``src.modules.feed_recommend.data_loader``. Per-user state references
restaurants by integer ``source_id``; the service validates existence
against the cache, hence no FK constraints.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1f4c7e9b2d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("address_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('geolocation', 'manual')",
            name="source_values",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_locations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_locations"),
        sa.UniqueConstraint("user_id", name="uq_user_locations_user"),
    )

    op.create_table(
        "user_restaurant_saves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_source_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_restaurant_saves_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_restaurant_saves"),
        sa.UniqueConstraint(
            "user_id",
            "restaurant_source_id",
            name="uq_user_restaurant_saves_user_restaurant",
        ),
    )
    op.create_index(
        "ix_user_restaurant_saves_user_id",
        "user_restaurant_saves",
        ["user_id"],
    )

    op.create_table(
        "user_restaurant_seen",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_source_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column(
            "seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('skip', 'view')",
            name="action_values",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_restaurant_seen_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_restaurant_seen"),
        sa.UniqueConstraint(
            "user_id",
            "restaurant_source_id",
            name="uq_user_restaurant_seen_user_restaurant",
        ),
    )
    op.create_index(
        "ix_user_restaurant_seen_user_id",
        "user_restaurant_seen",
        ["user_id"],
    )

    op.add_column(
        "users",
        sa.Column("price_band_cents", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dining_sessions",
        sa.Column("restaurant_source_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dining_sessions", "restaurant_source_id")
    op.drop_column("users", "price_band_cents")
    op.drop_index(
        "ix_user_restaurant_seen_user_id",
        table_name="user_restaurant_seen",
    )
    op.drop_table("user_restaurant_seen")
    op.drop_index(
        "ix_user_restaurant_saves_user_id",
        table_name="user_restaurant_saves",
    )
    op.drop_table("user_restaurant_saves")
    op.drop_table("user_locations")
