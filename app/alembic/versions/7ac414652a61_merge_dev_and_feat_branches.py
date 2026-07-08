"""merge dev and feat branches

Revision ID: 7ac414652a61
Revises: e5f6a7b8c9d0
Create Date: 2026-07-09 00:37:55.907350
"""

from collections.abc import Sequence



revision: str = '7ac414652a61'
down_revision: str | None = 'e5f6a7b8c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
