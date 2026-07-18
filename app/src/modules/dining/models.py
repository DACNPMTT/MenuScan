import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.modules.identity.models import PreferenceType

if TYPE_CHECKING:
    from src.modules.menu.models import FoodItem, Menu
    from src.modules.menu_scan.models import ScanSession


class DiningSessionMode(str, enum.Enum):
    PERSONAL = "PERSONAL"
    GROUP = "GROUP"


class DiningSessionStatus(str, enum.Enum):
    COLLECTING = "COLLECTING"
    SCANNING = "SCANNING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class RecommendationVerdict(str, enum.Enum):
    RECOMMENDED = "RECOMMENDED"
    OK = "OK"
    CAUTION = "CAUTION"
    AVOID = "AVOID"


class DiningSession(Base):
    __tablename__ = "dining_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_dining_sessions_created_by_user_id_users",
            ondelete="SET NULL",
        ),
    )
    scan_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "scan_sessions.id",
            name="fk_dining_sessions_scan_session_id_scan_sessions",
            ondelete="SET NULL",
        ),
        unique=True,
    )
    menu_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "menus.id",
            name="fk_dining_sessions_menu_id_menus",
            ondelete="SET NULL",
        ),
        unique=True,
    )
    mode: Mapped[DiningSessionMode] = mapped_column(
        Enum(DiningSessionMode, name="dining_session_mode"),
        nullable=False,
    )
    status: Mapped[DiningSessionStatus] = mapped_column(
        Enum(DiningSessionStatus, name="dining_session_status"),
        nullable=False,
        server_default=DiningSessionStatus.COLLECTING.value,
    )
    # No language column. A dining session is people sitting at a table, not a
    # locale: each diner reads the app in whatever language their own browser is
    # set to. The scan's translation target (ScanSession/Menu.target_language) and
    # the diner's profile language (User/FoodProfile.preferred_language) are
    # different things and both stay.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scan_session: Mapped["ScanSession | None"] = relationship()
    # Disambiguate: there are two FK paths between dining_sessions and menus now
    # (this pointer to the latest meal, and menus.dining_session_id for the whole
    # meal history). This relationship follows the latest-meal pointer.
    menu: Mapped["Menu | None"] = relationship(
        foreign_keys="DiningSession.menu_id"
    )
    invites: Mapped[list["DiningSessionInvite"]] = relationship(
        back_populates="dining_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    participants: Mapped[list["DiningSessionParticipant"]] = relationship(
        back_populates="dining_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recommendations: Mapped[list["FoodItemRecommendation"]] = relationship(
        back_populates="dining_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status != 'COMPLETED' OR "
            "(scan_session_id IS NOT NULL AND menu_id IS NOT NULL)",
            name="completed_has_scan_and_menu",
        ),
        Index("ix_dining_sessions_created_by_user_id", created_by_user_id),
        Index("ix_dining_sessions_scan_session_id", scan_session_id),
        Index("ix_dining_sessions_menu_id", menu_id),
    )


class DiningSessionInvite(Base):
    __tablename__ = "dining_session_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dining_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_sessions.id",
            name="fk_dining_session_invites_dining_session_id_dining_sessions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    use_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    dining_session: Mapped[DiningSession] = relationship(back_populates="invites")

    __table_args__ = (
        CheckConstraint("max_uses > 0", name="max_uses_positive"),
        CheckConstraint("use_count >= 0", name="use_count_non_negative"),
        CheckConstraint(
            "max_uses IS NULL OR use_count <= max_uses",
            name="use_count_within_max_uses",
        ),
        Index("ix_dining_session_invites_dining_session_id", dining_session_id),
    )


class DiningSessionParticipant(Base):
    __tablename__ = "dining_session_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dining_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_sessions.id",
            name="fk_dining_participants_dining_session_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_dining_session_participants_user_id_users",
            ondelete="SET NULL",
        ),
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dining_session: Mapped[DiningSession] = relationship(back_populates="participants")
    preferences: Mapped[list["DiningSessionParticipantPreference"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    selections: Mapped[list["DiningSessionParticipantSelection"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recommendation_breakdowns: Mapped[
        list["FoodItemRecommendationParticipantBreakdown"]
    ] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_dining_session_participants_dining_session_id", dining_session_id),
        Index("ix_dining_session_participants_user_id", user_id),
    )


class DiningSessionParticipantPreference(Base):
    __tablename__ = "dining_session_participant_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_session_participants.id",
            name="fk_dining_participant_preferences_participant_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    preference_type: Mapped[PreferenceType] = mapped_column(
        Enum(PreferenceType, name="preference_type"),
        nullable=False,
    )
    intensity: Mapped[int | None] = mapped_column(SmallInteger)
    importance: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="3",
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    participant: Mapped[DiningSessionParticipant] = relationship(
        back_populates="preferences"
    )

    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "code",
            "preference_type",
            name="uq_dining_participant_preferences_participant_code_type",
        ),
        CheckConstraint("intensity BETWEEN 0 AND 5", name="intensity"),
        CheckConstraint("importance BETWEEN 1 AND 5", name="importance"),
        Index(
            "ix_dining_session_participant_preferences_participant_id",
            participant_id,
        ),
    )


class DiningSessionParticipantSelection(Base):
    """A dish a guest picked in a group session, with how many and any note.

    One row per (participant, dish): the guest's picker replaces the whole set on
    every "chốt", so quantity is stored on the row rather than as duplicate rows.
    This is what lets the host see who ordered what, and what the per-person bill
    split is computed from.
    """

    __tablename__ = "dining_session_participant_selections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_session_participants.id",
            name="fk_dining_participant_selections_participant_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "food_items.id",
            name="fk_dining_participant_selections_food_item_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    participant: Mapped[DiningSessionParticipant] = relationship(
        back_populates="selections"
    )
    food_item: Mapped["FoodItem"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "food_item_id",
            name="uq_dining_participant_selections_participant_item",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index(
            "ix_dining_session_participant_selections_participant_id",
            participant_id,
        ),
        Index(
            "ix_dining_session_participant_selections_food_item_id",
            food_item_id,
        ),
    )


class FoodItemRecommendation(Base):
    __tablename__ = "food_item_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dining_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_sessions.id",
            name="fk_food_item_recommendations_dining_session_id_dining_sessions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "food_items.id",
            name="fk_food_item_recommendations_food_item_id_food_items",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    verdict: Mapped[RecommendationVerdict] = mapped_column(
        Enum(RecommendationVerdict, name="recommendation_verdict"),
        nullable=False,
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    explanation: Mapped[str | None] = mapped_column(Text)
    why_suitable: Mapped[str | None] = mapped_column(Text)
    why_not_suitable: Mapped[str | None] = mapped_column(Text)
    suggested_for: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    warning_for: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    fit_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    risk_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    warning_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    dining_session: Mapped[DiningSession] = relationship(
        back_populates="recommendations"
    )
    food_item: Mapped["FoodItem"] = relationship()
    participant_breakdowns: Mapped[
        list["FoodItemRecommendationParticipantBreakdown"]
    ] = relationship(
        back_populates="food_item_recommendation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "dining_session_id",
            "food_item_id",
            name="uq_food_item_recommendations_session_item",
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="score"),
        CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="confidence",
        ),
        Index("ix_food_item_recommendations_dining_session_id", dining_session_id),
        Index("ix_food_item_recommendations_food_item_id", food_item_id),
    )


class FoodItemRecommendationParticipantBreakdown(Base):
    __tablename__ = "food_item_recommendation_participant_breakdowns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    food_item_recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "food_item_recommendations.id",
            name="fk_food_item_rec_breakdowns_recommendation_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_session_participants.id",
            name="fk_food_item_recommendation_breakdowns_participant_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    verdict: Mapped[RecommendationVerdict] = mapped_column(
        Enum(RecommendationVerdict, name="recommendation_verdict"),
        nullable=False,
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    explanation: Mapped[str | None] = mapped_column(Text)
    fit_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    risk_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    food_item_recommendation: Mapped[FoodItemRecommendation] = relationship(
        back_populates="participant_breakdowns"
    )
    participant: Mapped[DiningSessionParticipant] = relationship(
        back_populates="recommendation_breakdowns"
    )

    __table_args__ = (
        UniqueConstraint(
            "food_item_recommendation_id",
            "participant_id",
            name="uq_food_item_rec_breakdowns_recommendation_participant",
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="score"),
        Index(
            "ix_food_item_recommendation_breakdowns_recommendation_id",
            food_item_recommendation_id,
        ),
        Index(
            "ix_food_item_recommendation_breakdowns_participant_id",
            participant_id,
        ),
    )
