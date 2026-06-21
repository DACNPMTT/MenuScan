"""Create the MenuScan MVP schema.

Revision ID: 001
Revises:
Create Date: 2026-06-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role = postgresql.ENUM("USER", "ADMIN", name="user_role")
user_status = postgresql.ENUM(
    "ACTIVE",
    "LOCKED",
    "DISABLED",
    name="user_status",
)
scan_status = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="scan_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=False)
    user_status.create(bind, checkfirst=False)
    scan_status.create(bind, checkfirst=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(150), nullable=True),
        sa.Column(
            "preferred_language",
            sa.String(10),
            server_default="vi",
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(
                "USER",
                "ADMIN",
                name="user_role",
                create_type=False,
            ),
            server_default="USER",
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "LOCKED",
                "DISABLED",
                name="user_status",
                create_type=False,
            ),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "preferred_language IN ('vi', 'en')",
            name="ck_users_preferred_language",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_magic_link_tokens_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_magic_link_tokens"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_magic_link_tokens_token_hash",
        ),
    )
    op.create_index(
        "ix_magic_link_tokens_email_created_at",
        "magic_link_tokens",
        ["email", sa.text("created_at DESC")],
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_rotated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.UniqueConstraint(
            "refresh_token_hash",
            name="uq_user_sessions_refresh_token_hash",
        ),
    )
    op.create_index(
        "ix_user_sessions_user_id",
        "user_sessions",
        ["user_id"],
    )

    op.create_table(
        "scan_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_object_key", sa.Text(), nullable=False),
        sa.Column("source_file_name", sa.String(255), nullable=False),
        sa.Column("source_mime_type", sa.String(100), nullable=False),
        sa.Column("source_file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "source_page_count",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("target_language", sa.String(10), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                name="scan_status",
                create_type=False,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("stage", sa.String(30), nullable=True),
        sa.Column(
            "progress",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status != 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_scan_sessions_completed_at",
        ),
        sa.CheckConstraint(
            "source_file_size BETWEEN 1 AND 10485760",
            name="ck_scan_sessions_file_size",
        ),
        sa.CheckConstraint(
            "status != 'FAILED' OR error_code IS NOT NULL",
            name="ck_scan_sessions_failed_error_code",
        ),
        sa.CheckConstraint(
            "source_mime_type IN "
            "('image/jpeg', 'image/png', 'image/webp', 'application/pdf')",
            name="ck_scan_sessions_mime_type",
        ),
        sa.CheckConstraint(
            "source_page_count BETWEEN 1 AND 5",
            name="ck_scan_sessions_page_count",
        ),
        sa.CheckConstraint(
            "progress BETWEEN 0 AND 100",
            name="ck_scan_sessions_progress",
        ),
        sa.CheckConstraint(
            "target_language IN ('vi', 'en')",
            name="ck_scan_sessions_target_language",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_scan_sessions_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scan_sessions"),
    )
    op.create_index(
        "ix_scan_sessions_user_id",
        "scan_sessions",
        ["user_id"],
    )

    op.create_table(
        "ocr_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "scan_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(10), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="ck_ocr_results_confidence",
        ),
        sa.CheckConstraint(
            "processing_time_ms >= 0",
            name="ck_ocr_results_processing_time",
        ),
        sa.ForeignKeyConstraint(
            ["scan_session_id"],
            ["scan_sessions.id"],
            name="fk_ocr_results_scan_session_id_scan_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ocr_results"),
        sa.UniqueConstraint(
            "scan_session_id",
            name="uq_ocr_results_scan_session_id",
        ),
    )

    op.create_table(
        "menus",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "scan_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_language", sa.String(10), nullable=True),
        sa.Column("target_language", sa.String(10), nullable=False),
        sa.Column("default_currency", sa.CHAR(3), nullable=True),
        sa.Column(
            "is_saved",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "NOT is_saved OR saved_at IS NOT NULL",
            name="ck_menus_saved_at",
        ),
        sa.CheckConstraint(
            "target_language IN ('vi', 'en')",
            name="ck_menus_target_language",
        ),
        sa.ForeignKeyConstraint(
            ["scan_session_id"],
            ["scan_sessions.id"],
            name="fk_menus_scan_session_id_scan_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_menus"),
        sa.UniqueConstraint(
            "scan_session_id",
            name="uq_menus_scan_session_id",
        ),
    )

    op.create_table(
        "food_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("menu_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("translated_name", sa.String(255), nullable=True),
        sa.Column("original_description", sa.Text(), nullable=True),
        sa.Column("translated_description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.CHAR(3), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="ck_food_items_confidence",
        ),
        sa.CheckConstraint(
            "price >= 0",
            name="ck_food_items_price_non_negative",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_food_items_sort_order",
        ),
        sa.ForeignKeyConstraint(
            ["menu_id"],
            ["menus.id"],
            name="fk_food_items_menu_id_menus",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_items"),
        sa.UniqueConstraint(
            "menu_id",
            "sort_order",
            name="uq_food_items_menu_id_sort_order",
        ),
    )
    op.create_index(
        "ix_food_items_menu_id",
        "food_items",
        ["menu_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_food_items_menu_id", table_name="food_items")
    op.drop_table("food_items")
    op.drop_table("menus")
    op.drop_table("ocr_results")
    op.drop_index("ix_scan_sessions_user_id", table_name="scan_sessions")
    op.drop_table("scan_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(
        "ix_magic_link_tokens_email_created_at",
        table_name="magic_link_tokens",
    )
    op.drop_table("magic_link_tokens")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    scan_status.drop(bind, checkfirst=False)
    user_status.drop(bind, checkfirst=False)
    user_role.drop(bind, checkfirst=False)
