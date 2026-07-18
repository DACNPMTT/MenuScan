import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CHAR,
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

if TYPE_CHECKING:
    from src.modules.menu_scan.models import ScanSession


class MenuStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scan_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "scan_sessions.id",
            name="fk_menus_scan_session_id_scan_sessions",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )
    # The group meal this menu belongs to, if it was scanned inside a dining
    # session. A session has many menus (one per meal/round); this is the
    # many-to-one that lets us list a group's meals. NULL for ordinary personal
    # scans. Not unique — that is the whole point of multi-meal.
    dining_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "dining_sessions.id",
            name="fk_menus_dining_session_id_dining_sessions",
            ondelete="SET NULL",
        ),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_language: Mapped[str | None] = mapped_column(String(10))
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    default_currency: Mapped[str | None] = mapped_column(CHAR(3))
    is_saved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    status: Mapped[MenuStatus] = mapped_column(
        Enum(MenuStatus, name="menu_status"),
        nullable=False,
        server_default=MenuStatus.DRAFT.value,
    )
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    scan_session: Mapped["ScanSession"] = relationship(back_populates="menu")
    food_items: Mapped[list["FoodItem"]] = relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="target_language",
        ),
        CheckConstraint(
            "NOT is_saved OR saved_at IS NOT NULL",
            name="saved_at",
        ),
        Index("ix_menus_deleted_at", deleted_at),
        Index("ix_menus_updated_at", updated_at),
        Index("ix_menus_dining_session_id", dining_session_id),
    )


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "menus.id",
            name="fk_food_items_menu_id_menus",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    translated_name: Mapped[str | None] = mapped_column(String(255))
    original_description: Mapped[str | None] = mapped_column(Text)
    translated_description: Mapped[str | None] = mapped_column(Text)
    assistant_summary: Mapped[str | None] = mapped_column(Text)
    main_ingredients: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    ingredient_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    flavor_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    texture_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    cooking_methods: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    spice_level: Mapped[int | None] = mapped_column(SmallInteger)
    sweetness_level: Mapped[int | None] = mapped_column(SmallInteger)
    saltiness_level: Mapped[int | None] = mapped_column(SmallInteger)
    sourness_level: Mapped[int | None] = mapped_column(SmallInteger)
    richness_level: Mapped[int | None] = mapped_column(SmallInteger)
    oiliness_level: Mapped[int | None] = mapped_column(SmallInteger)
    risk_notes: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    category: Mapped[str | None] = mapped_column(String(100))
    # LLM-inferred dietary metadata (shared taxonomy). Matched against the diner's
    # declared allergies / dietary_preferences to warn or flag dishes.
    allergens: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    dietary_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
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

    menu: Mapped[Menu] = relationship(back_populates="food_items")

    __table_args__ = (
        UniqueConstraint(
            "menu_id",
            "sort_order",
            name="uq_food_items_menu_id_sort_order",
        ),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint(
            "spice_level BETWEEN 0 AND 5",
            name="spice_level",
        ),
        CheckConstraint(
            "sweetness_level BETWEEN 0 AND 5",
            name="sweetness_level",
        ),
        CheckConstraint(
            "saltiness_level BETWEEN 0 AND 5",
            name="saltiness_level",
        ),
        CheckConstraint(
            "sourness_level BETWEEN 0 AND 5",
            name="sourness_level",
        ),
        CheckConstraint(
            "richness_level BETWEEN 0 AND 5",
            name="richness_level",
        ),
        CheckConstraint(
            "oiliness_level BETWEEN 0 AND 5",
            name="oiliness_level",
        ),
        CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="confidence",
        ),
        CheckConstraint("sort_order >= 0", name="sort_order"),
        Index("ix_food_items_menu_id", menu_id),
    )


class MenuHostSelection(Base):
    """The menu owner's own dish picks for a menu — the host's order draft.

    Guest picks live in dining_session_participant_selections; the host is not a
    participant, so their clicks had nowhere to persist and vanished on reload.
    This is that missing store: one row per (menu, dish), replaced whenever the
    host re-saves. Kept per menu (not per session) so it also survives multi-meal
    and ordinary personal menus.
    """

    __tablename__ = "menu_host_selections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "menus.id",
            name="fk_menu_host_selections_menu_id_menus",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    food_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "food_items.id",
            name="fk_menu_host_selections_food_item_id_food_items",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
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

    __table_args__ = (
        UniqueConstraint(
            "menu_id",
            "food_item_id",
            name="uq_menu_host_selections_menu_item",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_menu_host_selections_menu_id", menu_id),
    )
