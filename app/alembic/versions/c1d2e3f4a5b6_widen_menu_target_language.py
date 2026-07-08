"""widen menus.target_language to all supported languages

Revision ID: c1d2e3f4a5b6
Revises: a3c9e1d4b7f2
Create Date: 2026-07-08 05:00:00.000000

The scan_sessions target_language check was widened to the seven supported
languages in ccfae21342e0, but the menus table was missed. A scan targeting a
non vi/en language (e.g. 'fr') therefore passed scan-session validation and then
failed when the pipeline inserted the Menu row, with a CheckViolation on
ck_menus_ck_menus_target_language. Widen the menus constraint to match, and give
it the clean single-prefixed name the model expects.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "a3c9e1d4b7f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL_LANGUAGES = "target_language IN ('vi', 'en', 'zh', 'ja', 'ko', 'fr', 'th')"


def upgrade() -> None:
    # The metadata naming convention prepends ``ck_<table>_`` to the name passed
    # here, so "ck_menus_target_language" resolves to the actual DB constraint
    # ck_menus_ck_menus_target_language. Swap its condition to the 7 languages.
    op.drop_constraint("ck_menus_target_language", "menus", type_="check")
    op.create_check_constraint("ck_menus_target_language", "menus", _ALL_LANGUAGES)


def downgrade() -> None:
    op.drop_constraint("ck_menus_target_language", "menus", type_="check")
    op.create_check_constraint(
        "ck_menus_target_language",
        "menus",
        "target_language IN ('vi', 'en')",
    )
