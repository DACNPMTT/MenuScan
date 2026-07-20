"""merge feed recommendation and bill split heads

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7, b2e5d8f3c6a1
Create Date: 2026-07-21 00:00:00.000000
"""

from collections.abc import Sequence


revision: str = "c4d5e6f7a8b9"
down_revision: str | tuple[str, str] | None = (
    "b2c3d4e5f6a7",
    "b2e5d8f3c6a1",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join independent migration branches without schema changes."""


def downgrade() -> None:
    """Split independent migration branches without schema changes."""
