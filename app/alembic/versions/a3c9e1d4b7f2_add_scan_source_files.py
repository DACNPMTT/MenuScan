"""add scan_source_files and widen page count to 8

Revision ID: a3c9e1d4b7f2
Revises: f32b7c1a9e6d
Create Date: 2026-07-06 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a3c9e1d4b7f2"
down_revision: str | None = "f32b7c1a9e6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_source_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "scan_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "scan_sessions.id",
                name="fk_scan_source_files_scan_session_id_scan_sessions",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "page_count", sa.SmallInteger(), nullable=False, server_default="1"
        ),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "mime_type IN "
            "('image/jpeg', 'image/png', 'image/webp', 'application/pdf')",
            name="source_file_mime_type",
        ),
        sa.CheckConstraint(
            "file_size BETWEEN 1 AND 10485760", name="source_file_size"
        ),
        sa.CheckConstraint("sort_order >= 0", name="source_file_sort_order"),
    )
    op.create_index(
        "ix_scan_source_files_scan_session_id",
        "scan_source_files",
        ["scan_session_id"],
    )

    # Widen the per-scan page cap from 5 to 8 (multiple uploaded images).
    # Drop by every historical name (migration-built vs create_all-built dev DBs
    # produced different constraint names) then recreate at the canonical name.
    _drop_page_count_constraint()
    op.execute(
        "ALTER TABLE scan_sessions ADD CONSTRAINT ck_scan_sessions_page_count "
        "CHECK (source_page_count BETWEEN 1 AND 8)"
    )


def downgrade() -> None:
    _drop_page_count_constraint()
    op.execute(
        "ALTER TABLE scan_sessions ADD CONSTRAINT ck_scan_sessions_page_count "
        "CHECK (source_page_count BETWEEN 1 AND 5)"
    )
    op.drop_index(
        "ix_scan_source_files_scan_session_id", table_name="scan_source_files"
    )
    op.drop_table("scan_source_files")


def _drop_page_count_constraint() -> None:
    for name in (
        "ck_scan_sessions_page_count",
        "ck_scan_sessions_ck_scan_sessions_page_count",
        "page_count",
    ):
        op.execute(f'ALTER TABLE scan_sessions DROP CONSTRAINT IF EXISTS "{name}"')
