"""Bill lifecycle and totals computation.

This is the *domain service* required by issue #127's completion criteria:
"Tổng tiền được tính bởi domain service, không tin giá client gửi lên."

Hard rules enforced here (each maps to a bullet in the issue):
  1. A bill belongs to a user and a menu (``create_bill``).
  2. ``BillItem`` rows store an immutable name/price snapshot taken from the
     ``FoodItem`` at add-time (``add_item``) -- later edits to the menu never
     change an already-billed line (see ``test_menu_change_does_not_affect_
     existing_bill_item`` for the regression test).
  3. A bill has at least ``DRAFT`` / ``FINALIZED`` states; only ``DRAFT``
     bills can be mutated (``_ensure_mutable``).
  4. A single bill uses one currency; every item/adjustment must match it
     (``_ensure_currency``).
  5. All money math uses ``Decimal`` with explicit ``ROUND_HALF_UP`` to 2
     decimal places (``_round_money``) -- the price/quantity/amount the
     client sends is only ever an *input*; the totals stored on the row are
     always recomputed server-side from the snapshots.
  6. There is deliberately no "send order to the restaurant" operation
     anywhere in this module -- billing only reflects what the guest owes.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from src.modules.billing.exceptions import (
    BillAlreadyFinalizedError,
    BillNotFoundError,
    CurrencyMismatchError,
    EmptyBillError,
    FoodItemMissingPriceError,
    FoodItemNotFoundError,
    InvalidQuantityError,
    MenuNotFoundError,
    NegativeTotalError,
)
from src.modules.billing.models import (
    Bill,
    BillAdjustment,
    BillAdjustmentType,
    BillItem,
    BillStatus,
)
from src.modules.billing.repository import BillRepository
from src.modules.menu.models import FoodItem, Menu

_CENTS = Decimal("0.01")


def _round_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places using HALF_UP -- the one rounding rule."""
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillingService:
    """Orchestrates bill creation, line items, adjustments, and finalization."""

    def __init__(
        self,
        *,
        session: Session,
        repository: BillRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or BillRepository()
        self._clock = clock or _utcnow

    # --- Bill creation ----------------------------------------------------

    def create_bill(self, *, user_id: uuid.UUID, menu_id: uuid.UUID) -> Bill:
        """Create an empty DRAFT bill for ``user_id`` scoped to ``menu_id``."""
        menu = self._session.get(Menu, menu_id)
        if menu is None:
            raise MenuNotFoundError()

        bill = Bill(
            user_id=user_id,
            menu_id=menu_id,
            status=BillStatus.DRAFT,
            # Placeholder until the first item sets the real currency; a
            # DRAFT bill with zero items has no meaningful currency yet.
            currency=menu.default_currency or "VND",
            subtotal_amount=Decimal("0.00"),
            adjustment_total=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )
        return self._repository.add(self._session, bill)

    # --- Line items ---------------------------------------------------------

    def add_item(
        self,
        *,
        bill_id: uuid.UUID,
        food_item_id: uuid.UUID,
        quantity: int = 1,
    ) -> BillItem:
        """Snapshot ``food_item``'s current name/price onto a new bill line.

        The client may pass ``food_item_id`` and ``quantity`` only -- never a
        price. The unit price and line total are always derived from the
        ``FoodItem`` row read inside this call, never from caller input.
        """
        bill = self._get_mutable_bill(bill_id)

        if quantity <= 0:
            raise InvalidQuantityError()

        food_item = self._session.get(FoodItem, food_item_id)
        if food_item is None or food_item.menu_id != bill.menu_id:
            raise FoodItemNotFoundError()
        if food_item.price is None or food_item.currency is None:
            raise FoodItemMissingPriceError()

        self._ensure_currency(bill, food_item.currency)
        if not bill.items:
            bill.currency = food_item.currency

        line_total = _round_money(food_item.price * quantity)
        next_sort_order = len(bill.items)

        item = BillItem(
            bill_id=bill.id,
            food_item_id=food_item.id,
            name_snapshot=food_item.translated_name or food_item.original_name,
            unit_price_snapshot=food_item.price,
            currency=food_item.currency,
            quantity=quantity,
            line_total=line_total,
            sort_order=next_sort_order,
        )
        self._repository.add_item(self._session, item)
        bill.items.append(item)
        self._recompute_totals(bill)
        self._session.commit()
        return item

    # --- Adjustments ----------------------------------------------------------

    def add_adjustment(
        self,
        *,
        bill_id: uuid.UUID,
        adjustment_type: BillAdjustmentType,
        label: str,
        amount: Decimal,
    ) -> BillAdjustment:
        """Add a signed adjustment (discount/tax/surcharge/...) to the bill."""
        bill = self._get_mutable_bill(bill_id)

        rounded_amount = _round_money(amount)
        candidate_total = _round_money(
            bill.subtotal_amount + bill.adjustment_total + rounded_amount
        )
        if candidate_total < 0:
            raise NegativeTotalError()

        adjustment = BillAdjustment(
            bill_id=bill.id,
            type=adjustment_type,
            label=label,
            amount=rounded_amount,
        )
        self._repository.add_adjustment(self._session, adjustment)
        bill.adjustments.append(adjustment)
        self._recompute_totals(bill)
        self._session.commit()
        return adjustment

    # --- Finalization -----------------------------------------------------

    def finalize_bill(self, *, bill_id: uuid.UUID) -> Bill:
        """Transition a DRAFT bill with at least one item to FINALIZED.

        Finalization only locks the bill for the guest's payment record --
        it never triggers any "send to restaurant" workflow.
        """
        bill = self._get_mutable_bill(bill_id)
        if not bill.items:
            raise EmptyBillError()

        self._recompute_totals(bill)
        bill.status = BillStatus.FINALIZED
        bill.finalized_at = self._clock()
        bill.updated_at = bill.finalized_at
        self._session.commit()
        return bill

    # --- Internals ----------------------------------------------------------

    def _get_mutable_bill(self, bill_id: uuid.UUID) -> Bill:
        bill = self._repository.get_by_id(self._session, bill_id)
        if bill is None:
            raise BillNotFoundError()
        self._ensure_mutable(bill)
        return bill

    @staticmethod
    def _ensure_mutable(bill: Bill) -> None:
        if bill.status != BillStatus.DRAFT:
            raise BillAlreadyFinalizedError()

    @staticmethod
    def _ensure_currency(bill: Bill, currency: str) -> None:
        if bill.items and bill.currency != currency:
            raise CurrencyMismatchError()

    @staticmethod
    def _recompute_totals(bill: Bill) -> None:
        """Recompute subtotal/adjustment/total strictly from persisted rows.

        Never trusts any client-supplied total -- always derived bottom-up
        from ``bill.items`` (snapshots) and ``bill.adjustments``.
        """
        subtotal = _round_money(
            sum((item.line_total for item in bill.items), Decimal("0.00"))
        )
        adjustment_total = _round_money(
            sum((adj.amount for adj in bill.adjustments), Decimal("0.00"))
        )
        total = _round_money(subtotal + adjustment_total)
        if total < 0:
            raise NegativeTotalError()

        bill.subtotal_amount = subtotal
        bill.adjustment_total = adjustment_total
        bill.total_amount = total