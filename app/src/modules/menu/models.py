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
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
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
            "target_language IN ('vi', 'en')",
            name="target_language",
        ),
        CheckConstraint(
            "NOT is_saved OR saved_at IS NOT NULL",
            name="saved_at",
        ),
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
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    category: Mapped[str | None] = mapped_column(String(100))
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
            "confidence_score BETWEEN 0 AND 1",
            name="confidence",
        ),
        CheckConstraint("sort_order >= 0", name="sort_order"),
        Index("ix_food_items_menu_id", menu_id),
    )
