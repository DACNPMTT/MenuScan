"""drop the implicit personal dining sessions the scan used to create

Revision ID: c7a4e2b8f931
Revises: f1a2b3c4d5e6
Create Date: 2026-07-12 23:40:00.000000

Every scan used to silently create a PERSONAL dining session, a participant, and a
frozen copy of the diner's food profile, then score a verdict for every dish —
before any dish had the taste tags a verdict is scored from. The result was that
almost every dish came out "100/100 recommended".

Those rows are now gone from the code path, but the ones already in the database
would keep being served forever: the menu screen resolves verdicts by
`dining_sessions.menu_id`, finds the junk session, and reads its junk verdicts.
Deleting them is what makes the fix visible to existing users. Personal menus are
now scored live from the diner's current food profile instead, and persist nothing.

The selector is deliberately narrow. A session a user created through the API
always has an invite row and starts with `scan_session_id IS NULL`, so a genuine
user-created PERSONAL session is never matched. Participants, preferences,
recommendations and breakdowns all cascade.
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c7a4e2b8f931"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM dining_sessions
        WHERE mode = 'PERSONAL'
          AND scan_session_id IS NOT NULL
          AND id NOT IN (SELECT dining_session_id FROM dining_session_invites)
        """
    )


def downgrade() -> None:
    # Irreversible on purpose. These rows were generated noise scored against empty
    # tags; there is nothing worth restoring, and no way to reconstruct them anyway.
    pass
