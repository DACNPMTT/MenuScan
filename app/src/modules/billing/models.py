"""Billing domain models: bills, bill line items, and bill adjustments.

Design notes (see GitHub issue #127):
  - A bill belongs to exactly one user and one menu.
  - Bill items store an immutable name/price *snapshot* taken at the moment
    the item is added, so later edits to the menu/food item never change a
    previously billed amount.
  - A bill has at minimum two states: ``DRAFT`` (mutable) and ``FINALIZED``
    (immutable, totals locked).
  - A single bill always uses one currency; every item snapshot and every
    adjustment must match the bill's currency (enforced in the domain
    service, see ``src/modules/billing/service.py``).
  - Monetary columns use ``NUMERIC`` (never float) with explicit rounding
    handled in the domain service (``ROUND_HALF_UP`` to 2 decimal places).
  - This module intentionally has no concept of "send order to the
    restaurant" -- billing only models *what the user is charged for*.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    CHAR,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.modules.identity.models import User
    from src.modules.menu.models import FoodItem, Menu


class BillStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class BillAdjustmentType(str, enum.Enum):
    DISCOUNT = "DISCOUNT"
    SURCHARGE = "SURCHARGE"
    TAX = "TAX"
    SERVICE_CHARGE = "SERVICE_CHARGE"
    ROUNDING = "ROUNDING"


class BillAdjustmentCalculationType(str, enum.Enum):
    """How ``BillAdjustment.value`` should be turned into ``calculated_amount``.

    ``FIXED``: ``value`` is a flat money amount in the bill's currency.
    ``PERCENTAGE``: ``value`` is a percentage (0-100) applied to the bill's
    ``subtotal_amount`` at the time the adjustment is added/edited.
    """

    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_bills_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "menus.id",
            name="fk_bills_menu_id_menus",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus, name="bill_status"),
        nullable=False,
        server_default=BillStatus.DRAFT.value,
    )
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )
    adjustment_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        server_default="0",
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
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # How many people the host chose to split this bill across, recorded when
    # they finalize a group bill. It is what a guest opening the shared receipt
    # sees, so their per-person share matches the host's chosen headcount.
    # Null for solo/legacy bills that were never split.
    split_people_count: Mapped[int | None] = mapped_column(Integer)

    user: Mapped["User"] = relationship()
    menu: Mapped["Menu"] = relationship()
    items: Mapped[list["BillItem"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BillItem.sort_order",
    )
    adjustments: Mapped[list["BillAdjustment"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'FINALIZED')",
            name="status",
        ),
        CheckConstraint(
            "status != 'FINALIZED' OR finalized_at IS NOT NULL",
            name="finalized_at",
        ),
        CheckConstraint("subtotal_amount >= 0", name="subtotal_amount_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
        CheckConstraint(
            "split_people_count IS NULL OR split_people_count > 0",
            name="split_people_count_positive",
        ),
        Index("ix_bills_user_id", user_id),
        Index("ix_bills_menu_id", menu_id),
    )


class BillItem(Base):
    __tablename__ = "bill_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "bills.id",
            name="fk_bill_items_bill_id_bills",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    # Nullable + ON DELETE SET NULL: the snapshot columns below are the
    # source of truth for billing; this is kept only for traceability back
    # to the menu item that originated the line, and must never be joined
    # against to recompute a historical amount.
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "food_items.id",
            name="fk_bill_items_food_item_id_food_items",
            ondelete="SET NULL",
        ),
    )
    name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
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

    bill: Mapped[Bill] = relationship(back_populates="items")
    food_item: Mapped["FoodItem | None"] = relationship()

    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "unit_price_snapshot >= 0",
            name="unit_price_snapshot_non_negative",
        ),
        CheckConstraint("line_total >= 0", name="line_total_non_negative"),
        Index("ix_bill_items_bill_id", bill_id),
    )


class BillAdjustment(Base):
    __tablename__ = "bill_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "bills.id",
            name="fk_bill_adjustments_bill_id_bills",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    type: Mapped[BillAdjustmentType] = mapped_column(
        Enum(BillAdjustmentType, name="bill_adjustment_type"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    # How `value` below is interpreted -- a flat amount or a percentage of
    # the bill's subtotal at the time the adjustment was added/edited.
    calculation_type: Mapped[BillAdjustmentCalculationType] = mapped_column(
        Enum(BillAdjustmentCalculationType, name="bill_adjustment_calculation_type"),
        nullable=False,
        server_default=BillAdjustmentCalculationType.FIXED.value,
    )
    # The raw, unsigned magnitude entered by the server (a money amount for
    # FIXED, or 0-100 for PERCENTAGE). Never signed -- sign is derived from
    # `type` when computing `calculated_amount`.
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Signed, server-computed amount actually applied to the bill: negative
    # for discounts, positive for surcharges/tax/service charges/rounding.
    # Always derived server-side from `type`, `calculation_type`, and
    # `value` -- never trusted from the client.
    calculated_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    bill: Mapped[Bill] = relationship(back_populates="adjustments")

    __table_args__ = (
        CheckConstraint("value >= 0", name="value_non_negative"),
        CheckConstraint(
            "calculation_type != 'PERCENTAGE' OR value <= 100",
            name="percentage_value_within_bounds",
        ),
        Index("ix_bill_adjustments_bill_id", bill_id),
    )
