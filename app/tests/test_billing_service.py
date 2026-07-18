"""Integration tests for ``BillingService`` against a real PostgreSQL.

Gated by ``RUN_DATABASE_TESTS=1`` (same convention as
``test_database_integration.py``). The ``db_session`` fixture isolates each
test via savepoint rollback.

These tests map directly to the "Tiêu chí hoàn thành" in issue #127:
  - Tổng tiền được tính bởi domain service, không tin giá client gửi lên.
  - Menu thay đổi không làm đổi bill item snapshot.
  - (Migration/rollback is covered by ``test_database_integration.py`` once
    the migration has been applied; ``downgrade()`` is exercised manually.)
  - Không có nghiệp vụ gửi order đến nhà hàng (asserted by absence: no such
    method exists anywhere on ``BillingService``).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.modules.billing.exceptions import (
    AdjustmentLabelRequiredError,
    AdjustmentNotFoundError,
    BillAlreadyFinalizedError,
    BillNotFoundError,
    CurrencyMismatchError,
    EmptyBillError,
    FoodItemMissingPriceError,
    FoodItemNotFoundError,
    InvalidPeopleCountError,
    InvalidPercentageRangeError,
    InvalidQuantityError,
    NegativeTotalError,
)
from src.modules.billing.models import (
    Bill,
    BillAdjustmentCalculationType,
    BillAdjustmentType,
    BillStatus,
)
from src.modules.billing.service import BillSplit, BillingService, SplitShare
from src.modules.identity.models import User
from src.modules.menu.models import FoodItem, Menu
from src.modules.menu_scan.models import ScanSession, ScanStatus

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="PostgreSQL integration tests require RUN_DATABASE_TESTS=1",
)


def _make_user(session) -> User:
    user = User(email=f"billing-{uuid.uuid4()}@example.com")
    session.add(user)
    session.flush()
    return user


def _make_menu_with_items(session, user: User, *, currency: str = "VND") -> Menu:
    scan_session = ScanSession(
        user_id=user.id,
        source_object_key=f"scans/{uuid.uuid4()}.jpg",
        source_file_name="menu.jpg",
        source_mime_type="image/jpeg",
        source_file_size=1024,
        target_language="vi",
        status=ScanStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(scan_session)
    session.flush()

    menu = Menu(
        scan_session_id=scan_session.id,
        title="Quán test",
        target_language="vi",
        default_currency=currency,
    )
    session.add(menu)
    session.flush()

    pho = FoodItem(
        menu_id=menu.id,
        original_name="Phở bò",
        translated_name="Beef noodle soup",
        price=Decimal("65000.00"),
        currency=currency,
        sort_order=0,
    )
    com = FoodItem(
        menu_id=menu.id,
        original_name="Cơm tấm",
        translated_name="Broken rice",
        price=Decimal("45000.00"),
        currency=currency,
        sort_order=1,
    )
    session.add_all([pho, com])
    session.flush()
    return menu


def _items(session, menu: Menu) -> list[FoodItem]:
    return sorted(menu.food_items, key=lambda item: item.sort_order)


def test_create_bill_belongs_to_user_and_menu(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    service = BillingService(session=db_session)

    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    assert bill.user_id == user.id
    assert bill.menu_id == menu.id
    assert bill.status == BillStatus.DRAFT


def test_total_is_computed_by_service_not_trusted_from_client(db_session):
    """The service must derive totals from snapshots, ignoring any client total."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, com = _items(db_session, menu)
    service = BillingService(session=db_session)

    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=2)
    service.add_item(bill_id=bill.id, food_item_id=com.id, quantity=1)

    # 2 * 65000 + 1 * 45000 = 175000, no adjustments yet.
    assert bill.subtotal_amount == Decimal("175000.00")
    assert bill.adjustment_total == Decimal("0.00")
    assert bill.total_amount == Decimal("175000.00")


def test_add_item_falls_back_to_menu_default_currency(db_session):
    """A priced item with a null currency bills at the menu's default_currency.

    Regression: such items previously raised FoodItemMissingPriceError even
    though they have a price, breaking "create receipt".
    """
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user, currency="VND")
    item = FoodItem(
        menu_id=menu.id,
        original_name="Trà đá",
        price=Decimal("5000.00"),
        currency=None,  # only the menu-level default_currency is set
        sort_order=2,
    )
    db_session.add(item)
    db_session.flush()
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    line = service.add_item(bill_id=bill.id, food_item_id=item.id, quantity=2)

    assert line.currency == "VND"
    assert line.line_total == Decimal("10000.00")


def test_list_bills_for_user_returns_only_own_bills_newest_first(db_session):
    user = _make_user(db_session)
    other = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    other_menu = _make_menu_with_items(db_session, other)
    service = BillingService(session=db_session)

    older = service.create_bill(user_id=user.id, menu_id=menu.id)
    newer = service.create_bill(user_id=user.id, menu_id=menu.id)
    foreign = service.create_bill(user_id=other.id, menu_id=other_menu.id)

    # Postgres now() is transaction-scoped, so every row shares a timestamp.
    # Force distinct values to assert the ordering deterministically.
    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    db_session.flush()

    bills = service.list_bills_for_user(user_id=user.id)

    assert [bill.id for bill in bills] == [newer.id, older.id]
    assert foreign.id not in {bill.id for bill in bills}


def test_delete_bill_removes_it_with_its_items(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _com = _items(db_session, menu)
    service = BillingService(session=db_session)

    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    bill_id = bill.id

    service.delete_bill(bill_id=bill_id, user_id=user.id)

    assert service.list_bills_for_user(user_id=user.id) == []
    with pytest.raises(BillNotFoundError):
        service.get_bill_for_user(bill_id=bill_id, user_id=user.id)


def test_delete_bill_rejects_a_non_owner(db_session):
    owner = _make_user(db_session)
    intruder = _make_user(db_session)
    menu = _make_menu_with_items(db_session, owner)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=owner.id, menu_id=menu.id)

    with pytest.raises(BillNotFoundError):
        service.delete_bill(bill_id=bill.id, user_id=intruder.id)

    # Still there for its owner.
    assert service.get_bill_for_user(bill_id=bill.id, user_id=owner.id).id == bill.id


def test_vat_tip_and_surcharge_stack_on_the_subtotal(db_session):
    """The bill-calculator combo: VAT % + tip % (both on subtotal) + flat surcharge.

    Mirrors what MenuDetailPage previews client-side, so the receipt must match.
    """
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user, currency="VND")
    pho, com = _items(db_session, menu)
    service = BillingService(session=db_session)

    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)  # 65000
    service.add_item(bill_id=bill.id, food_item_id=com.id, quantity=1)  # 45000

    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.TAX,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="VAT",
        value=Decimal("10"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Tip",
        value=Decimal("5"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SURCHARGE,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Surcharge",
        value=Decimal("20000"),
    )

    # 110000 subtotal + 11000 VAT + 5500 tip + 20000 surcharge
    assert bill.subtotal_amount == Decimal("110000.00")
    assert bill.adjustment_total == Decimal("36500.00")
    assert bill.total_amount == Decimal("146500.00")


def test_add_item_still_rejects_item_without_a_price(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user, currency="VND")
    item = FoodItem(
        menu_id=menu.id,
        original_name="Món chưa có giá",
        price=None,
        currency=None,
        sort_order=2,
    )
    db_session.add(item)
    db_session.flush()
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    with pytest.raises(FoodItemMissingPriceError):
        service.add_item(bill_id=bill.id, food_item_id=item.id, quantity=1)


def test_bill_item_stores_name_and_price_snapshot(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)

    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    item = service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    assert item.name_snapshot == "Beef noodle soup"
    assert item.unit_price_snapshot == Decimal("65000.00")
    assert item.currency == "VND"
    assert item.line_total == Decimal("65000.00")


def test_menu_change_does_not_affect_existing_bill_item_snapshot(db_session):
    """Editing the FoodItem after billing must never change the bill item."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)

    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    item = service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    original_total = bill.total_amount

    # Restaurant changes the menu price after the order was billed.
    pho.price = Decimal("99000.00")
    pho.translated_name = "Beef noodle soup (large)"
    db_session.flush()

    db_session.refresh(item)
    db_session.refresh(bill)

    assert item.unit_price_snapshot == Decimal("65000.00")
    assert item.name_snapshot == "Beef noodle soup"
    assert bill.total_amount == original_total


def test_currency_must_be_consistent_within_one_bill(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user, currency="VND")
    pho, _ = _items(db_session, menu)

    # Same menu, but this item was scanned/entered with a different currency
    # (e.g. OCR misread) -- the bill must still reject mixing currencies.
    usd_item = FoodItem(
        menu_id=menu.id,
        original_name="Imported snack",
        translated_name="Imported snack",
        price=Decimal("3.50"),
        currency="USD",
        sort_order=2,
    )
    db_session.add(usd_item)
    db_session.flush()

    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    with pytest.raises(CurrencyMismatchError):
        service.add_item(bill_id=bill.id, food_item_id=usd_item.id, quantity=1)


def test_quantity_must_be_positive(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    with pytest.raises(InvalidQuantityError):
        service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=0)


def test_fixed_adjustment_applies_rounding_with_numeric_precision(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    # FIXED service charge on 65000, with a fractional value to exercise
    # HALF_UP rounding to 2 decimal places.
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Phí phục vụ",
        value=Decimal("6500.005"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Giảm giá thành viên",
        value=Decimal("5000"),
    )

    assert bill.adjustment_total == Decimal("1500.01")
    assert bill.total_amount == Decimal("66500.01")


def test_percentage_adjustment_is_computed_from_subtotal(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    adjustment = service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.TAX,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="VAT 10%",
        value=Decimal("10"),
    )

    assert adjustment.calculated_amount == Decimal("6500.00")
    assert bill.adjustment_total == Decimal("6500.00")
    assert bill.total_amount == Decimal("71500.00")


def test_percentage_adjustment_order_does_not_change_result(db_session):
    """Every adjustment is computed against subtotal, independent of order."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service_a = BillingService(session=db_session)
    bill_a = service_a.create_bill(user_id=user.id, menu_id=menu.id)
    service_a.add_item(bill_id=bill_a.id, food_item_id=pho.id, quantity=1)
    service_a.add_adjustment(
        bill_id=bill_a.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Phí phục vụ 10%",
        value=Decimal("10"),
    )
    service_a.add_adjustment(
        bill_id=bill_a.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Giảm giá 5%",
        value=Decimal("5"),
    )

    user_b = _make_user(db_session)
    menu_b = _make_menu_with_items(db_session, user_b)
    pho_b, _ = _items(db_session, menu_b)
    service_b = BillingService(session=db_session)
    bill_b = service_b.create_bill(user_id=user_b.id, menu_id=menu_b.id)
    service_b.add_item(bill_id=bill_b.id, food_item_id=pho_b.id, quantity=1)
    service_b.add_adjustment(
        bill_id=bill_b.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Giảm giá 5%",
        value=Decimal("5"),
    )
    service_b.add_adjustment(
        bill_id=bill_b.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Phí phục vụ 10%",
        value=Decimal("10"),
    )

    assert bill_a.total_amount == bill_b.total_amount


def test_percentage_adjustment_rejects_value_above_100(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    with pytest.raises(InvalidPercentageRangeError):
        service.add_adjustment(
            bill_id=bill.id,
            adjustment_type=BillAdjustmentType.DISCOUNT,
            calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
            label="Giảm giá quá tay",
            value=Decimal("150"),
        )


def test_adjustment_requires_a_non_blank_label(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    with pytest.raises(AdjustmentLabelRequiredError):
        service.add_adjustment(
            bill_id=bill.id,
            adjustment_type=BillAdjustmentType.SURCHARGE,
            calculation_type=BillAdjustmentCalculationType.FIXED,
            label="   ",
            value=Decimal("1000"),
        )


def test_update_adjustment_changes_value_and_recomputes_totals(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    adjustment = service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Giảm giá thành viên",
        value=Decimal("5000"),
    )

    updated = service.update_adjustment(
        bill_id=bill.id,
        adjustment_id=adjustment.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Giảm giá thành viên 10%",
        value=Decimal("10"),
    )

    assert updated.calculated_amount == Decimal("-6500.00")
    assert bill.adjustment_total == Decimal("-6500.00")
    assert bill.total_amount == Decimal("58500.00")


def test_remove_adjustment_recomputes_totals(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    adjustment = service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Giảm giá thành viên",
        value=Decimal("5000"),
    )

    bill = service.remove_adjustment(bill_id=bill.id, adjustment_id=adjustment.id)

    assert bill.adjustments == []
    assert bill.adjustment_total == Decimal("0.00")
    assert bill.total_amount == Decimal("65000.00")


def test_update_adjustment_raises_not_found_for_unknown_adjustment(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    with pytest.raises(AdjustmentNotFoundError):
        service.update_adjustment(
            bill_id=bill.id,
            adjustment_id=uuid.uuid4(),
            adjustment_type=BillAdjustmentType.DISCOUNT,
            calculation_type=BillAdjustmentCalculationType.FIXED,
            label="Không tồn tại",
            value=Decimal("1000"),
        )


def test_adjustment_cannot_push_total_negative(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    with pytest.raises(NegativeTotalError):
        service.add_adjustment(
            bill_id=bill.id,
            adjustment_type=BillAdjustmentType.DISCOUNT,
            calculation_type=BillAdjustmentCalculationType.FIXED,
            label="Giảm giá quá tay",
            value=Decimal("999999"),
        )


def test_cannot_finalize_an_empty_bill(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    with pytest.raises(EmptyBillError):
        service.finalize_bill(bill_id=bill.id)


def test_finalize_locks_the_bill_against_further_mutation(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    finalized = service.finalize_bill(bill_id=bill.id)

    assert finalized.status == BillStatus.FINALIZED
    assert finalized.finalized_at is not None

    with pytest.raises(BillAlreadyFinalizedError):
        service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    with pytest.raises(BillAlreadyFinalizedError):
        service.finalize_bill(bill_id=bill.id)


def test_get_bill_for_user_returns_bill_for_owner(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    found = service.get_bill_for_user(bill_id=bill.id, user_id=user.id)

    assert found.id == bill.id


def test_get_bill_for_user_raises_not_found_for_other_user(db_session):
    owner = _make_user(db_session)
    stranger = _make_user(db_session)
    menu = _make_menu_with_items(db_session, owner)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=owner.id, menu_id=menu.id)

    with pytest.raises(BillNotFoundError):
        service.get_bill_for_user(bill_id=bill.id, user_id=stranger.id)


def test_replace_items_adds_updates_and_removes_in_one_call(db_session):
    """Covers the issue #128 criterion: add/update/remove item tính lại subtotal."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, com = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    # Seed with both items.
    service.replace_items(
        bill_id=bill.id,
        user_id=user.id,
        items=[(pho.id, 1), (com.id, 2)],
    )
    assert bill.subtotal_amount == Decimal("155000.00")  # 65000 + 2*45000

    # Update pho's quantity and drop com entirely.
    service.replace_items(
        bill_id=bill.id,
        user_id=user.id,
        items=[(pho.id, 3)],
    )

    assert {item.food_item_id for item in bill.items} == {pho.id}
    assert bill.items[0].quantity == 3
    assert bill.subtotal_amount == Decimal("195000.00")  # 3 * 65000
    assert bill.total_amount == bill.subtotal_amount


def test_replace_items_with_empty_list_clears_bill_to_zero_subtotal(db_session):
    """Covers the issue #128 criterion: bill rỗng có subtotal bằng 0."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.replace_items(bill_id=bill.id, user_id=user.id, items=[(pho.id, 1)])

    service.replace_items(bill_id=bill.id, user_id=user.id, items=[])

    assert bill.items == []
    assert bill.subtotal_amount == Decimal("0.00")
    assert bill.total_amount == Decimal("0.00")


def test_replace_items_rejects_food_item_outside_bills_menu(db_session):
    """Covers the issue #128 criterion: food item phải thuộc menu của bill."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    other_menu = _make_menu_with_items(db_session, user)
    other_pho, _ = _items(db_session, other_menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    with pytest.raises(FoodItemNotFoundError):
        service.replace_items(
            bill_id=bill.id,
            user_id=user.id,
            items=[(other_pho.id, 1)],
        )


def test_replace_items_rejects_non_positive_quantity(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)

    with pytest.raises(InvalidQuantityError):
        service.replace_items(bill_id=bill.id, user_id=user.id, items=[(pho.id, 0)])


def test_replace_items_cannot_mutate_a_finalized_bill(db_session):
    """Covers the issue #128 criterion: chỉ bill DRAFT được sửa."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    service.finalize_bill(bill_id=bill.id)

    with pytest.raises(BillAlreadyFinalizedError):
        service.replace_items(bill_id=bill.id, user_id=user.id, items=[(pho.id, 2)])


def test_tax_and_surcharge_all_adjustment_types_accepted(db_session):
    """Covers issue #129: all four loại adjustment (Service charge, Tax, Discount, Other fee)."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.TAX,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="VAT 10%",
        value=Decimal("10"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Phí phục vụ",
        value=Decimal("5000"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Giảm giá khuyến mãi",
        value=Decimal("10000"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SURCHARGE,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Phụ thu cuối tuần",
        value=Decimal("3000"),
    )

    types = {adj.type for adj in bill.adjustments}
    assert BillAdjustmentType.TAX in types
    assert BillAdjustmentType.SERVICE_CHARGE in types
    assert BillAdjustmentType.DISCOUNT in types
    assert BillAdjustmentType.SURCHARGE in types
    # total = 65000 (subtotal) + 6500 (TAX 10%) + 5000 (SC) - 10000 (DISC) + 3000 (SC2)
    assert bill.total_amount == Decimal("69500.00")


def test_adjustment_add_then_update_then_remove_recomputes_correctly(db_session):
    """Covers issue #129 checklist: thêm/sửa/xóa adjustment tính lại total."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=2)
    # subtotal = 130000

    adj = service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Phí phục vụ ban đầu",
        value=Decimal("10000"),
    )
    assert bill.total_amount == Decimal("140000.00")

    service.update_adjustment(
        bill_id=bill.id,
        adjustment_id=adj.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Phí phục vụ 5%",
        value=Decimal("5"),
    )
    # 5% of 130000 = 6500
    assert bill.total_amount == Decimal("136500.00")

    service.remove_adjustment(bill_id=bill.id, adjustment_id=adj.id)
    assert bill.adjustment_total == Decimal("0.00")
    assert bill.total_amount == Decimal("130000.00")


def test_discount_at_exact_subtotal_brings_total_to_zero(db_session):
    """Covers issue #129: discount không làm total âm — boundary = 0 is allowed."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="Giảm 100%",
        value=Decimal("65000"),
    )

    assert bill.total_amount == Decimal("0.00")


def test_finalized_bill_blocks_add_and_remove_adjustment(db_session):
    """Covers issue #129 checklist: chỉ bill DRAFT được sửa (for adjustments)."""
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    adj = service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.TAX,
        calculation_type=BillAdjustmentCalculationType.FIXED,
        label="VAT",
        value=Decimal("5000"),
    )
    service.finalize_bill(bill_id=bill.id)

    with pytest.raises(BillAlreadyFinalizedError):
        service.add_adjustment(
            bill_id=bill.id,
            adjustment_type=BillAdjustmentType.DISCOUNT,
            calculation_type=BillAdjustmentCalculationType.FIXED,
            label="Giảm giá sau chốt",
            value=Decimal("1000"),
        )

    with pytest.raises(BillAlreadyFinalizedError):
        service.update_adjustment(
            bill_id=bill.id,
            adjustment_id=adj.id,
            adjustment_type=BillAdjustmentType.TAX,
            calculation_type=BillAdjustmentCalculationType.FIXED,
            label="VAT sửa",
            value=Decimal("9000"),
        )

    with pytest.raises(BillAlreadyFinalizedError):
        service.remove_adjustment(bill_id=bill.id, adjustment_id=adj.id)


def test_percentage_adjustment_uses_subtotal_not_running_total(db_session):
    """Thứ tự tính adjustment được tài liệu hóa: mỗi PERCENTAGE tính độc lập từ subtotal.

    Nếu service charge 10% chạy trước và TAX 10% tính trên *running total* thì
    tax sẽ là 10% × (subtotal + service_charge), khác với 10% × subtotal.
    Test này xác minh tax chỉ tính từ subtotal gốc (65000), không phụ thuộc
    vào adjustment đã thêm trước đó -- đây chính là quy tắc thứ tự được ghi trong
    service docstring và api-endpoints.md (issue #129).
    """
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)
    # subtotal = 65000

    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="Phí phục vụ 10%",
        value=Decimal("10"),
    )
    tax_adj = service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.TAX,
        calculation_type=BillAdjustmentCalculationType.PERCENTAGE,
        label="VAT 10%",
        value=Decimal("10"),
    )

    # Both must be 10% of SUBTOTAL (65000) = 6500 each, not cumulative
    assert tax_adj.calculated_amount == Decimal("6500.00")
    assert bill.adjustment_total == Decimal("13000.00")  # 6500 + 6500
    assert bill.total_amount == Decimal("78000.00")  # 65000 + 13000


def test_billing_service_has_no_send_order_to_restaurant_capability():
    """Billing never triggers a restaurant-facing order workflow (per spec).

    Issue #128 added ``get_bill_for_user`` and ``replace_items``.
    Issue #129 confirmed that ``add_adjustment``, ``update_adjustment``,
    ``remove_adjustment``, and ``finalize_bill`` are the only adjustment/
    lifecycle operations exposed -- no restaurant-order method was added.
    """
    public_methods = {
        name
        for name in dir(BillingService)
        if not name.startswith("_") and callable(getattr(BillingService, name))
    }
    assert public_methods == {
        "add_adjustment",
        "add_item",
        "create_bill",
        # Owner-scoped removal of the diner's own bill.
        "delete_bill",
        "finalize_bill",
        "get_bill_for_user",
        # Read-only bill history listing; still no restaurant-order operation.
        "list_bills_for_user",
        # Read-only reads backing the guest-facing shared receipt (finalized
        # bills only, gated upstream by the dining invite token) -- still no
        # restaurant-order operation.
        "list_finalized_bills_for_menus",
        "remove_adjustment",
        "replace_items",
        "split_bill",
        "split_for_display",
        "update_adjustment",
    }


# ---------------------------------------------------------------------------
# Bill split (issue #129 / [S2-12])
# ---------------------------------------------------------------------------

_ONE_CENT = Decimal("0.01")


def _bill_with_total(
    session,
    user: User,
    *,
    currency: str,
    total: Decimal,
) -> Bill:
    """Build a DRAFT bill whose ``total_amount`` is exactly ``total``.

    Creates a throwaway menu with a single food item priced at ``total`` so the
    one-line bill totals to the requested amount, exercising the same Decimal
    snapshot path used in production (no float anywhere).
    """
    scan_session = ScanSession(
        user_id=user.id,
        source_object_key=f"scans/{uuid.uuid4()}.jpg",
        source_file_name="menu.jpg",
        source_mime_type="image/jpeg",
        source_file_size=1024,
        target_language="vi",
        status=ScanStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(scan_session)
    session.flush()
    menu = Menu(
        scan_session_id=scan_session.id,
        title="Split test menu",
        target_language="vi",
        default_currency=currency,
    )
    session.add(menu)
    session.flush()
    food_item = FoodItem(
        menu_id=menu.id,
        original_name="Món đơn",
        translated_name="Single item",
        price=total,
        currency=currency,
        sort_order=0,
    )
    session.add(food_item)
    session.flush()
    service = BillingService(session=session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=food_item.id, quantity=1)
    return bill


def _amounts(split: BillSplit) -> list[Decimal]:
    return [share.amount for share in split.shares]


def test_split_evenly_when_total_divisible(db_session):
    """100.00 / 2 -> two exact halves, no remainder."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)

    split = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=2)

    assert split.base_share == Decimal("50.00")
    assert split.remainder_units == 0
    assert _amounts(split) == [Decimal("50.00"), Decimal("50.00")]
    assert sum(_amounts(split), Decimal("0.00")) == bill.total_amount


def test_split_distributes_remainder_deterministically(db_session):
    """100.00 / 3 -> the first person absorbs the leftover cent."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)

    split = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=3)

    assert split.base_share == Decimal("33.33")
    assert split.remainder_units == 1
    assert _amounts(split) == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert sum(_amounts(split), Decimal("0.00")) == Decimal("100.00")


@pytest.mark.parametrize(
    "currency, total, people",
    [
        ("USD", Decimal("100.00"), 3),
        ("USD", Decimal("100.00"), 7),
        ("USD", Decimal("99.99"), 2),
        ("USD", Decimal("0.03"), 4),
        ("VND", Decimal("175000.00"), 3),
        ("VND", Decimal("100000.00"), 7),
        ("EUR", Decimal("250.00"), 9),
        ("JPY", Decimal("1000.00"), 3),
    ],
)
def test_split_shares_sum_exactly_to_total(db_session, currency, total, people):
    """Invariant: shares always sum back to total, differing by <= 1 cent.

    Multiple currencies are covered; precision follows the system-wide 2-dp
    money model (VND/JPY totals are stored as NUMERIC(14,2) too).
    """
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency=currency, total=total)
    service = BillingService(session=db_session)

    split = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=people)

    assert split.currency == currency
    assert split.people_count == people
    assert len(split.shares) == people
    amounts = _amounts(split)
    assert sum(amounts, Decimal("0.00")) == bill.total_amount
    assert max(amounts) - min(amounts) <= _ONE_CENT


def test_split_single_person_returns_full_total(db_session):
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)

    split = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=1)

    assert split.shares == [SplitShare(person=1, amount=Decimal("100.00"))]
    assert split.remainder_units == 0


def test_split_rejects_fewer_than_one_person(db_session):
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)

    with pytest.raises(InvalidPeopleCountError):
        service.split_bill(bill_id=bill.id, user_id=user.id, people_count=0)


def test_split_never_uses_floating_point(db_session):
    """All money in the split result must be Decimal, never float."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)

    split = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=3)

    assert isinstance(split.total_amount, Decimal)
    assert isinstance(split.base_share, Decimal)
    assert all(isinstance(share.amount, Decimal) for share in split.shares)
    assert all(not isinstance(share.amount, float) for share in split.shares)


def test_split_reflects_changes_to_items(db_session):
    """Split recomputes from the current total after the bill changes."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    food_item_id = bill.items[0].food_item_id
    service = BillingService(session=db_session)

    first = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=3)
    assert sum(_amounts(first), Decimal("0.00")) == Decimal("100.00")

    # Add the same item again -> total doubles to 200.00.
    service.add_item(bill_id=bill.id, food_item_id=food_item_id, quantity=1)

    second = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=3)
    assert bill.total_amount == Decimal("200.00")
    assert sum(_amounts(second), Decimal("0.00")) == Decimal("200.00")
    assert max(_amounts(second)) - min(_amounts(second)) <= _ONE_CENT


def test_split_is_scoped_to_owner(db_session):
    """A non-owner must not be able to split someone else's bill (404)."""
    user = _make_user(db_session)
    other = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)

    with pytest.raises(BillNotFoundError):
        service.split_bill(bill_id=bill.id, user_id=other.id, people_count=2)


def test_finalized_bill_can_still_be_split(db_session):
    """Split is a read-only computation, so a FINALIZED bill is still splittable."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="USD", total=Decimal("100.00"))
    service = BillingService(session=db_session)
    service.finalize_bill(bill_id=bill.id)

    split = service.split_bill(bill_id=bill.id, user_id=user.id, people_count=4)

    assert sum(_amounts(split), Decimal("0.00")) == Decimal("100.00")
    assert len(split.shares) == 4


# ---------------------------------------------------------------------------
# Shared receipt: finalize headcount + guest-facing finalized-bill reads
# ---------------------------------------------------------------------------


def test_finalize_persists_split_people_count(db_session):
    """The headcount the host chose at finalize is stored on the bill."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="VND", total=Decimal("540000.00"))
    service = BillingService(session=db_session)

    finalized = service.finalize_bill(bill_id=bill.id, people_count=4)

    assert finalized.split_people_count == 4


def test_finalize_without_people_count_leaves_bill_unsplit(db_session):
    """Finalizing with no headcount keeps split_people_count null (solo bill)."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="VND", total=Decimal("100000.00"))
    service = BillingService(session=db_session)

    finalized = service.finalize_bill(bill_id=bill.id)

    assert finalized.split_people_count is None


def test_finalize_rejects_non_positive_people_count(db_session):
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="VND", total=Decimal("100000.00"))
    service = BillingService(session=db_session)

    with pytest.raises(InvalidPeopleCountError):
        service.finalize_bill(bill_id=bill.id, people_count=0)


def test_list_finalized_bills_for_menus_returns_only_finalized(db_session):
    """Guest-facing read exposes finalized bills only, never a DRAFT."""
    user = _make_user(db_session)
    finalized_bill = _bill_with_total(
        db_session, user, currency="VND", total=Decimal("540000.00")
    )
    draft_bill = _bill_with_total(
        db_session, user, currency="VND", total=Decimal("120000.00")
    )
    service = BillingService(session=db_session)
    service.finalize_bill(bill_id=finalized_bill.id, people_count=3)

    menu_ids = [finalized_bill.menu_id, draft_bill.menu_id]
    found = service.list_finalized_bills_for_menus(menu_ids=menu_ids)

    assert [bill.id for bill in found] == [finalized_bill.id]
    assert found[0].split_people_count == 3


def test_list_finalized_bills_for_menus_empty_when_no_menu_ids(db_session):
    service = BillingService(session=db_session)
    assert service.list_finalized_bills_for_menus(menu_ids=[]) == []


def test_split_for_display_matches_persisted_headcount(db_session):
    """The guest's per-person share uses the host's finalized headcount."""
    user = _make_user(db_session)
    bill = _bill_with_total(db_session, user, currency="VND", total=Decimal("540000.00"))
    service = BillingService(session=db_session)
    finalized = service.finalize_bill(bill_id=bill.id, people_count=4)

    split = service.split_for_display(
        bill=finalized, people_count=finalized.split_people_count
    )

    assert split.people_count == 4
    assert split.base_share == Decimal("135000.00")
    assert sum(_amounts(split), Decimal("0.00")) == Decimal("540000.00")
