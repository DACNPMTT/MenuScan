"""add split_people_count to bills

Revision ID: a1f4c7e9b2d5
Revises: e4f5a6b7c8d9
Create Date: 2026-07-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f4c7e9b2d5"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bills",
        sa.Column("split_people_count", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "split_people_count_positive",
        "bills",
        "split_people_count IS NULL OR split_people_count > 0",
    )


def downgrade() -> None:
    op.drop_constraint("split_people_count_positive", "bills", type_="check")
    op.drop_column("bills", "split_people_count")
