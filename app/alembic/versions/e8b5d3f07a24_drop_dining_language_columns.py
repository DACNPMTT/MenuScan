"""drop the language columns from the dining tables

Revision ID: e8b5d3f07a24
Revises: c7a4e2b8f931
Create Date: 2026-07-13 10:20:00.000000

A dining session is people sitting at a table, not a locale. Each diner reads the
app in whatever language their own browser is set to, so asking the host to pick a
"session language" — and then asking every guest to pick one again on the join
screen — was a question with no consequence: nothing downstream ever read either
column. The scan's translation target came from the upload form, and the join
page's UI language came from i18next either way.

Do NOT confuse these with the two language concepts that stay:
  - ScanSession.target_language / Menu.target_language — what the menu is
    translated INTO. Real, used, keep.
  - User.preferred_language / FoodProfile.preferred_language — the diner's own UI
    language, synced with the language switcher. Real, used, keep.

The columns are NOT NULL with no default, so this cannot be a code-only removal:
leaving them would break every INSERT. Postgres drops the column-local CHECK
constraints (ck_dining_sessions_target_language,
ck_dining_session_participants_preferred_language) along with the columns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e8b5d3f07a24"
down_revision: str | None = "c7a4e2b8f931"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("dining_session_participants", "preferred_language")
    op.drop_column("dining_sessions", "target_language")


def downgrade() -> None:
    # Recreated with a default so existing rows can be backfilled; the original
    # columns had none, which is why they could not simply be abandoned.
    op.add_column(
        "dining_sessions",
        sa.Column(
            "target_language",
            sa.String(10),
            nullable=False,
            server_default="vi",
        ),
    )
    op.create_check_constraint(
        "ck_dining_sessions_target_language",
        "dining_sessions",
        "target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
    )
    op.add_column(
        "dining_session_participants",
        sa.Column(
            "preferred_language",
            sa.String(10),
            nullable=False,
            server_default="vi",
        ),
    )
    op.create_check_constraint(
        "ck_dining_session_participants_preferred_language",
        "dining_session_participants",
        "preferred_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
    )
