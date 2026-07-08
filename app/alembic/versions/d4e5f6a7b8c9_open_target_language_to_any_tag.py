"""open target_language to any well-formed language tag

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-07-08 05:30:00.000000

The menu is translated by the LLM, which can target any language, so gating
target_language on a fixed 7-language whitelist is an artificial limit. Replace
the IN (...) checks on scan_sessions and menus with a format check that accepts
any lowercase BCP-47-ish tag (e.g. 'vi', 'en', 'zh', 'pt-br'), bounded by the
column's 10-char width. Raw SQL is used so the exact (naming-convention-mangled)
constraint names are targeted precisely.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE scan_sessions DROP CONSTRAINT ck_scan_sessions_target_language")
    op.execute(
        "ALTER TABLE scan_sessions ADD CONSTRAINT ck_scan_sessions_target_language "
        "CHECK (target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$')"
    )
    op.execute("ALTER TABLE menus DROP CONSTRAINT ck_menus_ck_menus_target_language")
    op.execute(
        "ALTER TABLE menus ADD CONSTRAINT ck_menus_ck_menus_target_language "
        "CHECK (target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$')"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE scan_sessions DROP CONSTRAINT ck_scan_sessions_target_language")
    op.execute(
        "ALTER TABLE scan_sessions ADD CONSTRAINT ck_scan_sessions_target_language "
        "CHECK (target_language IN ('vi', 'en', 'zh', 'ja', 'ko', 'fr', 'th'))"
    )
    op.execute("ALTER TABLE menus DROP CONSTRAINT ck_menus_ck_menus_target_language")
    op.execute(
        "ALTER TABLE menus ADD CONSTRAINT ck_menus_ck_menus_target_language "
        "CHECK (target_language IN ('vi', 'en'))"
    )
