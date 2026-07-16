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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from src.modules.billing.exceptions import (
    AdjustmentLabelRequiredError,
    AdjustmentNotFoundError,
    BillAlreadyFinalizedError,
    BillNotFoundError,
    CurrencyMismatchError,
    EmptyBillError,
    FoodItemMissingPriceError,
    FoodItemNotFoundError,
    InvalidAdjustmentValueError,
    InvalidPeopleCountError,
    InvalidPercentageRangeError,
    InvalidQuantityError,
    MenuNotFoundError,
    NegativeTotalError,
)
from src.modules.billing.models import (
    Bill,
    BillAdjustment,
    BillAdjustmentCalculationType,
    BillAdjustmentType,
    BillItem,
    BillStatus,
)
from src.modules.billing.repository import BillRepository
from src.modules.menu.models import FoodItem, Menu

_CENTS = Decimal("0.01")

# Sign applied to every computed adjustment amount, keyed by adjustment
# type. DISCOUNT always reduces the total; every other type increases it.
# This is the one place the sign convention lives -- callers only ever
# supply an unsigned ``value``.
_ADJUSTMENT_SIGN: dict[BillAdjustmentType, int] = {
    BillAdjustmentType.DISCOUNT: -1,
    BillAdjustmentType.SURCHARGE: 1,
    BillAdjustmentType.TAX: 1,
    BillAdjustmentType.SERVICE_CHARGE: 1,
    BillAdjustmentType.ROUNDING: 1,
}

# A PERCENTAGE adjustment's `value` must fall within this inclusive range.
_MIN_PERCENTAGE = Decimal("0")
_MAX_PERCENTAGE = Decimal("100")


def _round_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places using HALF_UP -- the one rounding rule."""
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SplitShare:
    """One person's share of a split bill (service-level DTO)."""

    person: int
    amount: Decimal


@dataclass(frozen=True)
class BillSplit:
    """Result of splitting a bill evenly among N people.

    ``shares`` always sums exactly to ``total_amount``: the per-person base is
    floored to the cent and the non-negative remainder (in whole cents) is
    handed out one cent at a time to the first ``remainder_units`` people, so
    no money is lost and the split is deterministic. All money is ``Decimal``
    -- never float. Precision follows the system-wide 2-decimal money model.
    """

    bill_id: uuid.UUID
    currency: str
    total_amount: Decimal
    people_count: int
    base_share: Decimal
    remainder_units: int
    shares: list[SplitShare] = field(default_factory=list)


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
        added = self._repository.add(self._session, bill)
        self._session.commit()
        return added

    # --- Reads --------------------------------------------------------------

    def get_bill_for_user(self, *, bill_id: uuid.UUID, user_id: uuid.UUID) -> Bill:
        """Return ``bill_id`` only if it belongs to ``user_id`` (404 otherwise).

        Not-found and not-owned are intentionally indistinguishable to the
        caller -- both surface as ``BillNotFoundError`` so the API never
        confirms a bill's existence to a non-owner.
        """
        bill = self._repository.get_by_id_for_user(self._session, bill_id, user_id)
        if bill is None:
            raise BillNotFoundError()
        return bill

    def list_bills_for_user(self, *, user_id: uuid.UUID) -> list[Bill]:
        """Every bill owned by ``user_id``, most recent first (bill history)."""
        return self._repository.list_for_user(self._session, user_id)

    def delete_bill(self, *, bill_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete one of the user's own bills; items/adjustments cascade.

        A non-owner (or missing bill) gets ``BillNotFoundError``, never a
        confirmation that the bill exists. Finalized bills may be deleted too --
        the receipt is the diner's own record, not the restaurant's.
        """
        bill = self.get_bill_for_user(bill_id=bill_id, user_id=user_id)
        self._repository.delete(self._session, bill)
        self._session.commit()

    def split_bill(
        self,
        *,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        people_count: int,
    ) -> BillSplit:
        """Split ``bill.total_amount`` evenly among ``people_count`` people.

        Pure computation -- the bill is not mutated, so a DRAFT bill can be
        previewed and a FINALIZED bill can still be split. The per-person base
        is floored to the cent and the remainder distributed to the first
        people so ``sum(shares) == total_amount`` exactly, deterministically.
        """
        if people_count < 1:
            raise InvalidPeopleCountError()

        bill = self.get_bill_for_user(bill_id=bill_id, user_id=user_id)

        total = _round_money(bill.total_amount)
        base = (total / people_count).quantize(_CENTS, rounding=ROUND_DOWN)
        # Whole-cent units left over after every person gets ``base``. Always
        # non-negative because ``base`` floors, and always an exact multiple
        # of one cent because both ``total`` and ``base`` are 2-decimal.
        remainder_units = int(
            ((total - base * people_count) / _CENTS).to_integral_value()
        )

        shares = [
            SplitShare(
                person=index + 1,
                amount=base + _CENTS if index < remainder_units else base,
            )
            for index in range(people_count)
        ]
        return BillSplit(
            bill_id=bill.id,
            currency=bill.currency,
            total_amount=total,
            people_count=people_count,
            base_share=base,
            remainder_units=remainder_units,
            shares=shares,
        )

    # --- Line items ---------------------------------------------------------

    @staticmethod
    def _resolve_currency(food_item: FoodItem) -> str | None:
        """The item's currency, falling back to its menu's default_currency.

        A parsed item often carries a price but a null ``currency`` (only the
        menu-level ``default_currency`` was inferred). Treating that as "no
        price" wrongly blocks billing, so resolve it against the menu here.
        """
        if food_item.currency:
            return food_item.currency
        menu = food_item.menu
        return menu.default_currency if menu else None

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
        currency = self._resolve_currency(food_item)
        if food_item.price is None or currency is None:
            raise FoodItemMissingPriceError()

        self._ensure_currency(bill, currency)
        if not bill.items:
            bill.currency = currency

        line_total = _round_money(food_item.price * quantity)
        next_sort_order = len(bill.items)

        item = BillItem(
            bill_id=bill.id,
            food_item_id=food_item.id,
            name_snapshot=food_item.translated_name or food_item.original_name,
            unit_price_snapshot=food_item.price,
            currency=currency,
            quantity=quantity,
            line_total=line_total,
            sort_order=next_sort_order,
        )
        self._repository.add_item(self._session, item)
        bill.items.append(item)
        self._recompute_totals(bill)
        self._session.commit()
        return item

    def replace_items(
        self,
        *,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
        items: list[tuple[uuid.UUID, int]],
    ) -> Bill:
        """Replace every line item on the bill with ``items`` and recompute totals.

        ``items`` is the *desired end state*, expressed as
        ``(food_item_id, quantity)`` pairs: a food item present in the list is
        added or updated to that quantity, and any existing line whose food
        item is absent from the list is removed. Duplicate ``food_item_id``
        entries are merged by summing their quantities so the call is
        idempotent regardless of how the caller grouped them.
        """
        bill = self.get_bill_for_user(bill_id=bill_id, user_id=user_id)
        self._ensure_mutable(bill)

        merged_quantities: dict[uuid.UUID, int] = {}
        for food_item_id, quantity in items:
            merged_quantities[food_item_id] = (
                merged_quantities.get(food_item_id, 0) + quantity
            )

        self._repository.clear_items(self._session, bill)
        new_currency: str | None = None

        for sort_order, (food_item_id, quantity) in enumerate(
            merged_quantities.items()
        ):
            if quantity <= 0:
                raise InvalidQuantityError()

            food_item = self._session.get(FoodItem, food_item_id)
            if food_item is None or food_item.menu_id != bill.menu_id:
                raise FoodItemNotFoundError()
            currency = self._resolve_currency(food_item)
            if food_item.price is None or currency is None:
                raise FoodItemMissingPriceError()

            if new_currency is None:
                new_currency = currency
            elif currency != new_currency:
                raise CurrencyMismatchError()

            line_total = _round_money(food_item.price * quantity)
            item = BillItem(
                bill_id=bill.id,
                food_item_id=food_item.id,
                name_snapshot=food_item.translated_name or food_item.original_name,
                unit_price_snapshot=food_item.price,
                currency=currency,
                quantity=quantity,
                line_total=line_total,
                sort_order=sort_order,
            )
            self._repository.add_item(self._session, item)
            bill.items.append(item)

        if new_currency is not None:
            bill.currency = new_currency

        self._recompute_totals(bill)
        self._session.commit()
        return bill

    # --- Adjustments ----------------------------------------------------------

    def add_adjustment(
        self,
        *,
        bill_id: uuid.UUID,
        adjustment_type: BillAdjustmentType,
        calculation_type: BillAdjustmentCalculationType,
        label: str,
        value: Decimal,
    ) -> BillAdjustment:
        """Add a discount/tax/surcharge/... adjustment to the bill.

        ``value`` is always an *unsigned* magnitude supplied by the caller:
        a flat money amount when ``calculation_type`` is ``FIXED``, or a
        percentage (0-100 inclusive) of the bill's *current*
        ``subtotal_amount`` when ``calculation_type`` is ``PERCENTAGE``.
        The signed, rounded ``calculated_amount`` actually applied to the
        bill is always derived here -- never trusted from the client.

        Ordering rule (documented per issue #129): every adjustment,
        whether FIXED or PERCENTAGE, is computed independently against the
        bill's line-item ``subtotal_amount`` -- never against a
        running/cumulative total that includes other adjustments. This
        keeps the result independent of the order adjustments were added
        in, which matters because every adjustment must show its own label
        and ``calculated_amount`` on the receipt.
        """
        bill = self._get_mutable_bill(bill_id)
        calculated_amount = self._calculate_adjustment_amount(
            bill=bill,
            adjustment_type=adjustment_type,
            calculation_type=calculation_type,
            value=value,
        )

        label = self._validate_label(label)
        candidate_total = _round_money(
            bill.subtotal_amount + bill.adjustment_total + calculated_amount
        )
        if candidate_total < 0:
            raise NegativeTotalError()

        adjustment = BillAdjustment(
            bill_id=bill.id,
            type=adjustment_type,
            label=label,
            calculation_type=calculation_type,
            value=value,
            calculated_amount=calculated_amount,
        )
        self._repository.add_adjustment(self._session, adjustment)
        bill.adjustments.append(adjustment)
        self._recompute_totals(bill)
        self._session.commit()
        return adjustment

    def update_adjustment(
        self,
        *,
        bill_id: uuid.UUID,
        adjustment_id: uuid.UUID,
        adjustment_type: BillAdjustmentType,
        calculation_type: BillAdjustmentCalculationType,
        label: str,
        value: Decimal,
    ) -> BillAdjustment:
        """Edit an existing adjustment in place and recompute totals."""
        bill = self._get_mutable_bill(bill_id)
        adjustment = self._repository.get_adjustment(
            self._session, bill_id, adjustment_id
        )
        if adjustment is None:
            raise AdjustmentNotFoundError()

        calculated_amount = self._calculate_adjustment_amount(
            bill=bill,
            adjustment_type=adjustment_type,
            calculation_type=calculation_type,
            value=value,
            exclude_adjustment_id=adjustment.id,
        )
        label = self._validate_label(label)

        other_adjustments_total = _round_money(
            sum(
                (
                    adj.calculated_amount
                    for adj in bill.adjustments
                    if adj.id != adjustment.id
                ),
                Decimal("0.00"),
            )
        )
        candidate_total = _round_money(
            bill.subtotal_amount + other_adjustments_total + calculated_amount
        )
        if candidate_total < 0:
            raise NegativeTotalError()

        adjustment.type = adjustment_type
        adjustment.calculation_type = calculation_type
        adjustment.label = label
        adjustment.value = value
        adjustment.calculated_amount = calculated_amount
        self._recompute_totals(bill)
        self._session.commit()
        return adjustment

    def remove_adjustment(
        self,
        *,
        bill_id: uuid.UUID,
        adjustment_id: uuid.UUID,
    ) -> Bill:
        """Remove an adjustment from a DRAFT bill and recompute totals."""
        bill = self._get_mutable_bill(bill_id)
        adjustment = self._repository.get_adjustment(
            self._session, bill_id, adjustment_id
        )
        if adjustment is None:
            raise AdjustmentNotFoundError()

        self._repository.remove_adjustment(self._session, bill, adjustment)
        self._recompute_totals(bill)
        self._session.commit()
        return bill

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
    def _validate_label(label: str) -> str:
        label = label.strip()
        if not label:
            raise AdjustmentLabelRequiredError()
        return label

    @staticmethod
    def _calculate_adjustment_amount(
        *,
        bill: Bill,
        adjustment_type: BillAdjustmentType,
        calculation_type: BillAdjustmentCalculationType,
        value: Decimal,
        exclude_adjustment_id: uuid.UUID | None = None,
    ) -> Decimal:
        """Derive the signed, rounded ``calculated_amount`` server-side.

        Never trusts a client-supplied amount: only an unsigned ``value``
        (flat money for FIXED, 0-100 percentage for PERCENTAGE) comes from
        the caller. See ``add_adjustment`` for the ordering rule that
        PERCENTAGE is always computed against ``bill.subtotal_amount``.
        """
        del exclude_adjustment_id  # reserved for future cumulative modes
        if value < 0:
            raise InvalidAdjustmentValueError()

        sign = _ADJUSTMENT_SIGN[adjustment_type]
        if calculation_type == BillAdjustmentCalculationType.PERCENTAGE:
            if value < _MIN_PERCENTAGE or value > _MAX_PERCENTAGE:
                raise InvalidPercentageRangeError()
            magnitude = _round_money(bill.subtotal_amount * value / Decimal("100"))
        else:
            magnitude = _round_money(value)

        return _round_money(Decimal(sign) * magnitude)

    @staticmethod
    def _recompute_totals(bill: Bill) -> None:
        """Recompute subtotal/adjustment/total strictly from persisted rows.

        Never trusts any client-supplied total -- always derived bottom-up
        from ``bill.items`` (snapshots) and ``bill.adjustments``
        (``calculated_amount``, the server-derived signed amount).
        """
        subtotal = _round_money(
            sum((item.line_total for item in bill.items), Decimal("0.00"))
        )
        adjustment_total = _round_money(
            sum(
                (adj.calculated_amount for adj in bill.adjustments),
                Decimal("0.00"),
            )
        )
        total = _round_money(subtotal + adjustment_total)
        if total < 0:
            raise NegativeTotalError()

        bill.subtotal_amount = subtotal
        bill.adjustment_total = adjustment_total
        bill.total_amount = total
