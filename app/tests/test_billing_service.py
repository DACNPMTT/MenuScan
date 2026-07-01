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
    FoodItemNotFoundError,
    InvalidPercentageRangeError,
    InvalidQuantityError,
    NegativeTotalError,
)
from src.modules.billing.models import (
    BillAdjustmentCalculationType,
    BillAdjustmentType,
    BillStatus,
)
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
    assert bill.total_amount == Decimal("78000.00")       # 65000 + 13000


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
        "create_bill",
        "get_bill_for_user",
        "add_item",
        "replace_items",
        "add_adjustment",
        "update_adjustment",
        "remove_adjustment",
        "finalize_bill",
    }