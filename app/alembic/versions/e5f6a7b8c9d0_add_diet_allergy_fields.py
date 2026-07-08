"""add allergy/diet fields to users and food_items

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-08 06:00:00.000000

Powers the dietary preferences & allergy feature:
  * users.allergies / users.dietary_preferences — what the diner declares.
  * food_items.allergens / food_items.dietary_tags — what the LLM infers per
    dish, matched against the diner's declarations to warn/flag.
All default to an empty array so existing rows are unaffected.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ARRAY = postgresql.ARRAY(sa.Text())
_EMPTY = sa.text("'{}'::text[]")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("allergies", _ARRAY, nullable=False, server_default=_EMPTY),
    )
    op.add_column(
        "users",
        sa.Column(
            "dietary_preferences", _ARRAY, nullable=False, server_default=_EMPTY
        ),
    )
    op.add_column(
        "food_items",
        sa.Column("allergens", _ARRAY, nullable=False, server_default=_EMPTY),
    )
    op.add_column(
        "food_items",
        sa.Column("dietary_tags", _ARRAY, nullable=False, server_default=_EMPTY),
    )


def downgrade() -> None:
    op.drop_column("food_items", "dietary_tags")
    op.drop_column("food_items", "allergens")
    op.drop_column("users", "dietary_preferences")
    op.drop_column("users", "allergies")
