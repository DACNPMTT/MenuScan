"""SQLAlchemy models for the feed_recommend module.

Three per-user tables that reference restaurants from the JSON dataset by
integer ``source_id`` — there is intentionally no ``restaurants`` table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class UserLocation(Base):
    """One cached lat/lng per user, written when they open the Discovery feed.

    1:1 with ``users`` via the UNIQUE constraint on ``user_id``. ``source``
    records whether the diner shared their browser geolocation or picked a
    city-center fallback so the UI can offer to switch later.
    """

    __tablename__ = "user_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_user_locations_user_id_users", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    address_text: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('geolocation', 'manual')",
            name="source_values",
        ),
    )


class UserRestaurantSave(Base):
    """A restaurant the diner bookmarked from the feed."""

    __tablename__ = "user_restaurant_saves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_user_restaurant_saves_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    restaurant_source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)  # reserved for future folders
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # composite unique keeps saves idempotent; the NAMING_CONVENTION in
        # core.database would also derive this name — kept explicit so the
        # constraint survives even if the convention changes.
        # The UNIQUE below is also created by the migration as a separate
        # ``uq_user_restaurant_saves_user_restaurant``; the inline declaration
        # would conflict on rerun, so it is intentionally omitted here.
        Index("ix_user_restaurant_saves_user_id", user_id),
    )


class UserRestaurantSeen(Base):
    """A restaurant the diner has already passed on (or saved) — not resurfaced.

    First interaction wins (UNIQUE on ``user_id, restaurant_source_id``), so
    skip-then-save keeps the original ``skip`` action and the card still leaves
    the feed (because ``save`` also writes an implicit ``view`` here).
    """

    __tablename__ = "user_restaurant_seen"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_user_restaurant_seen_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    restaurant_source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "action IN ('skip', 'view')",
            name="action_values",
        ),
        Index("ix_user_restaurant_seen_user_id", user_id),
    )
