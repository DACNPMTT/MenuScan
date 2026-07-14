"""add dining recommendation schema

Revision ID: 8a9b0c1d2e3f
Revises: 7ac414652a61
Create Date: 2026-07-11 00:00:00.000000

Adds the target schema for the AI dining assistant:
  * persistent user food profiles;
  * personal/group dining sessions with QR invites and participant snapshots;
  * richer menu item assistant fields;
  * per-session item recommendations and optional participant breakdowns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "8a9b0c1d2e3f"
down_revision: str | None = "7ac414652a61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


preference_type = postgresql.ENUM(
    "LIKE",
    "DISLIKE",
    "AVOID",
    "ALLERGY",
    "DIETARY_RULE",
    name="preference_type",
)
dining_session_mode = postgresql.ENUM(
    "PERSONAL",
    "GROUP",
    name="dining_session_mode",
)
dining_session_status = postgresql.ENUM(
    "COLLECTING",
    "SCANNING",
    "COMPLETED",
    "CLOSED",
    name="dining_session_status",
)
recommendation_verdict = postgresql.ENUM(
    "RECOMMENDED",
    "OK",
    "CAUTION",
    "AVOID",
    name="recommendation_verdict",
)

_TEXT_ARRAY = postgresql.ARRAY(sa.Text())
_EMPTY_TEXT_ARRAY = sa.text("'{}'::text[]")


def upgrade() -> None:
    bind = op.get_bind()
    preference_type.create(bind, checkfirst=False)
    dining_session_mode.create(bind, checkfirst=False)
    dining_session_status.create(bind, checkfirst=False)
    recommendation_verdict.create(bind, checkfirst=False)

    _add_food_item_assistant_columns()
    _create_food_profile_tables()
    _create_dining_session_tables()
    _create_recommendation_tables()


def downgrade() -> None:
    op.drop_table("food_item_recommendation_participant_breakdowns")
    op.drop_table("food_item_recommendations")
    op.drop_table("dining_session_participant_preferences")
    op.drop_table("dining_session_participants")
    op.drop_table("dining_session_invites")
    op.drop_table("dining_sessions")
    op.drop_table("food_profile_preferences")
    op.drop_index("uq_food_profiles_user_default", table_name="food_profiles")
    op.drop_table("food_profiles")
    _drop_food_item_assistant_columns()

    bind = op.get_bind()
    recommendation_verdict.drop(bind, checkfirst=False)
    dining_session_status.drop(bind, checkfirst=False)
    dining_session_mode.drop(bind, checkfirst=False)
    preference_type.drop(bind, checkfirst=False)


def _add_food_item_assistant_columns() -> None:
    op.add_column("food_items", sa.Column("assistant_summary", sa.Text()))
    op.add_column(
        "food_items",
        sa.Column(
            "main_ingredients",
            _TEXT_ARRAY,
            nullable=False,
            server_default=_EMPTY_TEXT_ARRAY,
        ),
    )
    op.add_column(
        "food_items",
        sa.Column(
            "ingredient_tags",
            _TEXT_ARRAY,
            nullable=False,
            server_default=_EMPTY_TEXT_ARRAY,
        ),
    )
    op.add_column(
        "food_items",
        sa.Column(
            "flavor_tags",
            _TEXT_ARRAY,
            nullable=False,
            server_default=_EMPTY_TEXT_ARRAY,
        ),
    )
    op.add_column(
        "food_items",
        sa.Column(
            "texture_tags",
            _TEXT_ARRAY,
            nullable=False,
            server_default=_EMPTY_TEXT_ARRAY,
        ),
    )
    op.add_column(
        "food_items",
        sa.Column(
            "cooking_methods",
            _TEXT_ARRAY,
            nullable=False,
            server_default=_EMPTY_TEXT_ARRAY,
        ),
    )
    op.add_column("food_items", sa.Column("spice_level", sa.SmallInteger()))
    op.add_column("food_items", sa.Column("sweetness_level", sa.SmallInteger()))
    op.add_column("food_items", sa.Column("saltiness_level", sa.SmallInteger()))
    op.add_column("food_items", sa.Column("sourness_level", sa.SmallInteger()))
    op.add_column("food_items", sa.Column("richness_level", sa.SmallInteger()))
    op.add_column("food_items", sa.Column("oiliness_level", sa.SmallInteger()))
    op.add_column("food_items", sa.Column("risk_notes", sa.Text()))

    op.create_check_constraint(
        "ck_food_items_spice_level",
        "food_items",
        "spice_level BETWEEN 0 AND 5",
    )
    op.create_check_constraint(
        "ck_food_items_sweetness_level",
        "food_items",
        "sweetness_level BETWEEN 0 AND 5",
    )
    op.create_check_constraint(
        "ck_food_items_saltiness_level",
        "food_items",
        "saltiness_level BETWEEN 0 AND 5",
    )
    op.create_check_constraint(
        "ck_food_items_sourness_level",
        "food_items",
        "sourness_level BETWEEN 0 AND 5",
    )
    op.create_check_constraint(
        "ck_food_items_richness_level",
        "food_items",
        "richness_level BETWEEN 0 AND 5",
    )
    op.create_check_constraint(
        "ck_food_items_oiliness_level",
        "food_items",
        "oiliness_level BETWEEN 0 AND 5",
    )


def _drop_food_item_assistant_columns() -> None:
    for constraint in (
        "ck_food_items_oiliness_level",
        "ck_food_items_richness_level",
        "ck_food_items_sourness_level",
        "ck_food_items_saltiness_level",
        "ck_food_items_sweetness_level",
        "ck_food_items_spice_level",
    ):
        op.drop_constraint(constraint, "food_items", type_="check")

    for column in (
        "risk_notes",
        "oiliness_level",
        "richness_level",
        "sourness_level",
        "saltiness_level",
        "sweetness_level",
        "spice_level",
        "cooking_methods",
        "texture_tags",
        "flavor_tags",
        "ingredient_tags",
        "main_ingredients",
        "assistant_summary",
    ):
        op.drop_column("food_items", column)


def _create_food_profile_tables() -> None:
    op.create_table(
        "food_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(150), nullable=False),
        sa.Column("preferred_language", sa.String(10), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("notes", sa.Text()),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "preferred_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="ck_food_profiles_preferred_language",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_food_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_profiles"),
    )
    op.create_index("ix_food_profiles_user_id", "food_profiles", ["user_id"])
    op.create_index(
        "uq_food_profiles_user_default",
        "food_profiles",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true AND deleted_at IS NULL"),
    )

    op.create_table(
        "food_profile_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column(
            "preference_type",
            postgresql.ENUM(
                "LIKE",
                "DISLIKE",
                "AVOID",
                "ALLERGY",
                "DIETARY_RULE",
                name="preference_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("intensity", sa.SmallInteger()),
        sa.Column(
            "importance",
            sa.SmallInteger(),
            server_default="3",
            nullable=False,
        ),
        sa.Column("note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "intensity BETWEEN 0 AND 5",
            name="ck_food_profile_preferences_intensity",
        ),
        sa.CheckConstraint(
            "importance BETWEEN 1 AND 5",
            name="ck_food_profile_preferences_importance",
        ),
        sa.ForeignKeyConstraint(
            ["food_profile_id"],
            ["food_profiles.id"],
            name="fk_food_profile_preferences_food_profile_id_food_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_profile_preferences"),
        sa.UniqueConstraint(
            "food_profile_id",
            "code",
            "preference_type",
            name="uq_food_profile_preferences_profile_code_type",
        ),
    )
    op.create_index(
        "ix_food_profile_preferences_food_profile_id",
        "food_profile_preferences",
        ["food_profile_id"],
    )


def _create_dining_session_tables() -> None:
    op.create_table(
        "dining_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("scan_session_id", postgresql.UUID(as_uuid=True)),
        sa.Column("menu_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "mode",
            postgresql.ENUM(
                "PERSONAL",
                "GROUP",
                name="dining_session_mode",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "COLLECTING",
                "SCANNING",
                "COMPLETED",
                "CLOSED",
                name="dining_session_status",
                create_type=False,
            ),
            server_default="COLLECTING",
            nullable=False,
        ),
        sa.Column("target_language", sa.String(10), nullable=False),
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
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="ck_dining_sessions_target_language",
        ),
        sa.CheckConstraint(
            "status != 'COMPLETED' OR "
            "(scan_session_id IS NOT NULL AND menu_id IS NOT NULL)",
            name="ck_dining_sessions_completed_has_scan_and_menu",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_dining_sessions_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scan_session_id"],
            ["scan_sessions.id"],
            name="fk_dining_sessions_scan_session_id_scan_sessions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["menu_id"],
            ["menus.id"],
            name="fk_dining_sessions_menu_id_menus",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dining_sessions"),
        sa.UniqueConstraint("scan_session_id", name="uq_dining_sessions_scan_session_id"),
        sa.UniqueConstraint("menu_id", name="uq_dining_sessions_menu_id"),
    )
    op.create_index(
        "ix_dining_sessions_created_by_user_id",
        "dining_sessions",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_dining_sessions_scan_session_id",
        "dining_sessions",
        ["scan_session_id"],
    )
    op.create_index("ix_dining_sessions_menu_id", "dining_sessions", ["menu_id"])

    op.create_table(
        "dining_session_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dining_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("max_uses", sa.Integer()),
        sa.Column("use_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_uses > 0",
            name="ck_dining_session_invites_max_uses_positive",
        ),
        sa.CheckConstraint(
            "use_count >= 0",
            name="ck_dining_session_invites_use_count_non_negative",
        ),
        sa.CheckConstraint(
            "max_uses IS NULL OR use_count <= max_uses",
            name="ck_dining_session_invites_use_count_within_max_uses",
        ),
        sa.ForeignKeyConstraint(
            ["dining_session_id"],
            ["dining_sessions.id"],
            name="fk_dining_session_invites_dining_session_id_dining_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dining_session_invites"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_dining_session_invites_token_hash",
        ),
    )
    op.create_index(
        "ix_dining_session_invites_dining_session_id",
        "dining_session_invites",
        ["dining_session_id"],
    )

    op.create_table(
        "dining_session_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dining_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("display_name", sa.String(150), nullable=False),
        sa.Column("preferred_language", sa.String(10), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "preferred_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="ck_dining_session_participants_preferred_language",
        ),
        sa.ForeignKeyConstraint(
            ["dining_session_id"],
            ["dining_sessions.id"],
            name="fk_dining_participants_dining_session_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_dining_session_participants_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dining_session_participants"),
    )
    op.create_index(
        "ix_dining_session_participants_dining_session_id",
        "dining_session_participants",
        ["dining_session_id"],
    )
    op.create_index(
        "ix_dining_session_participants_user_id",
        "dining_session_participants",
        ["user_id"],
    )

    op.create_table(
        "dining_session_participant_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column(
            "preference_type",
            postgresql.ENUM(
                "LIKE",
                "DISLIKE",
                "AVOID",
                "ALLERGY",
                "DIETARY_RULE",
                name="preference_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("intensity", sa.SmallInteger()),
        sa.Column(
            "importance",
            sa.SmallInteger(),
            server_default="3",
            nullable=False,
        ),
        sa.Column("note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "intensity BETWEEN 0 AND 5",
            name="ck_dining_session_participant_preferences_intensity",
        ),
        sa.CheckConstraint(
            "importance BETWEEN 1 AND 5",
            name="ck_dining_session_participant_preferences_importance",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["dining_session_participants.id"],
            name="fk_dining_participant_preferences_participant_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_dining_session_participant_preferences",
        ),
        sa.UniqueConstraint(
            "participant_id",
            "code",
            "preference_type",
            name="uq_dining_participant_preferences_participant_code_type",
        ),
    )
    op.create_index(
        "ix_dining_session_participant_preferences_participant_id",
        "dining_session_participant_preferences",
        ["participant_id"],
    )


def _create_recommendation_tables() -> None:
    op.create_table(
        "food_item_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dining_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "verdict",
            postgresql.ENUM(
                "RECOMMENDED",
                "OK",
                "CAUTION",
                "AVOID",
                name="recommendation_verdict",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("explanation", sa.Text()),
        sa.Column("why_suitable", sa.Text()),
        sa.Column("why_not_suitable", sa.Text()),
        sa.Column(
            "suggested_for",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "warning_for",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "fit_reasons",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "risk_reasons",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "warning_reasons",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Numeric(5, 4)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_food_item_recommendations_score",
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="ck_food_item_recommendations_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["dining_session_id"],
            ["dining_sessions.id"],
            name="fk_food_item_recommendations_dining_session_id_dining_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"],
            ["food_items.id"],
            name="fk_food_item_recommendations_food_item_id_food_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_item_recommendations"),
        sa.UniqueConstraint(
            "dining_session_id",
            "food_item_id",
            name="uq_food_item_recommendations_session_item",
        ),
    )
    op.create_index(
        "ix_food_item_recommendations_dining_session_id",
        "food_item_recommendations",
        ["dining_session_id"],
    )
    op.create_index(
        "ix_food_item_recommendations_food_item_id",
        "food_item_recommendations",
        ["food_item_id"],
    )

    op.create_table(
        "food_item_recommendation_participant_breakdowns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "food_item_recommendation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "verdict",
            postgresql.ENUM(
                "RECOMMENDED",
                "OK",
                "CAUTION",
                "AVOID",
                name="recommendation_verdict",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("explanation", sa.Text()),
        sa.Column(
            "fit_reasons",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "risk_reasons",
            _TEXT_ARRAY,
            server_default=_EMPTY_TEXT_ARRAY,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_food_item_recommendation_breakdowns_score",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_recommendation_id"],
            ["food_item_recommendations.id"],
            name="fk_food_item_rec_breakdowns_recommendation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["dining_session_participants.id"],
            name="fk_food_item_recommendation_breakdowns_participant_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_food_item_recommendation_participant_breakdowns",
        ),
        sa.UniqueConstraint(
            "food_item_recommendation_id",
            "participant_id",
            name="uq_food_item_rec_breakdowns_recommendation_participant",
        ),
    )
    op.create_index(
        "ix_food_item_recommendation_breakdowns_recommendation_id",
        "food_item_recommendation_participant_breakdowns",
        ["food_item_recommendation_id"],
    )
    op.create_index(
        "ix_food_item_recommendation_breakdowns_participant_id",
        "food_item_recommendation_participant_breakdowns",
        ["participant_id"],
    )
