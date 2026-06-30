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
    BillAlreadyFinalizedError,
    BillNotFoundError,
    CurrencyMismatchError,
    EmptyBillError,
    FoodItemNotFoundError,
    InvalidQuantityError,
    NegativeTotalError,
)
from src.modules.billing.models import BillAdjustmentType, BillStatus
from src.modules.billing.service import BillingService
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


def test_adjustment_applies_rounding_with_numeric_precision(db_session):
    user = _make_user(db_session)
    menu = _make_menu_with_items(db_session, user)
    pho, _ = _items(db_session, menu)
    service = BillingService(session=db_session)
    bill = service.create_bill(user_id=user.id, menu_id=menu.id)
    service.add_item(bill_id=bill.id, food_item_id=pho.id, quantity=1)

    # 10% service charge on 65000, with a fractional discount to exercise
    # HALF_UP rounding to 2 decimal places.
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.SERVICE_CHARGE,
        label="Phí phục vụ 10%",
        amount=Decimal("6500.005"),
    )
    service.add_adjustment(
        bill_id=bill.id,
        adjustment_type=BillAdjustmentType.DISCOUNT,
        label="Giảm giá thành viên",
        amount=Decimal("-5000"),
    )

    assert bill.adjustment_total == Decimal("1500.01")
    assert bill.total_amount == Decimal("66500.01")


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
            label="Giảm giá quá tay",
            amount=Decimal("-999999"),
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


def test_billing_service_has_no_send_order_to_restaurant_capability():
    """Billing never triggers a restaurant-facing order workflow (per spec).

    Issue #128 added ``get_bill_for_user`` (ownership-scoped read for
    ``GET /bills/{bill_id}``) and ``replace_items`` (add/update/remove in one
    call for ``PATCH /bills/{bill_id}/items``); the assertion below was
    updated accordingly. Crucially, no restaurant-order method was added.
    """
    public_methods = {
        name
        for name in dir(BillingService)
        if not name.startswith("_") and callable(getattr(BillingService, name))
    }
    assert public_methods == {
        "create_bill",
        "get_bill_for_user",
        "add_item",
        "replace_items",
        "add_adjustment",
        "finalize_bill",
    }