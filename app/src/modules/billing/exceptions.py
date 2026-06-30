"""Billing-module application errors.

Both extend ``core.errors.ApplicationError`` and are auto-mapped to the
standard error envelope by ``application_error_handler``.
"""

from __future__ import annotations

from src.core.errors import ApplicationError


class MenuNotFoundError(ApplicationError):
    """Raised when the menu referenced by a new bill does not exist (404)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="MENU_NOT_FOUND",
            message="Không tìm thấy menu cho hóa đơn này.",
        )


class FoodItemNotFoundError(ApplicationError):
    """Raised when a referenced food item does not exist (404)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="FOOD_ITEM_NOT_FOUND",
            message="Không tìm thấy món ăn này trên menu.",
        )


class BillNotFoundError(ApplicationError):
    """Raised when a bill cannot be found, or does not belong to the user (404)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="BILL_NOT_FOUND",
            message="Không tìm thấy hóa đơn.",
        )


class BillAlreadyFinalizedError(ApplicationError):
    """Raised when mutating a bill that is no longer in DRAFT status (409)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="BILL_ALREADY_FINALIZED",
            message="Hóa đơn đã chốt và không thể chỉnh sửa.",
        )


class EmptyBillError(ApplicationError):
    """Raised when finalizing a bill that has no line items (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="EMPTY_BILL",
            message="Hóa đơn chưa có món nào để chốt.",
        )


class CurrencyMismatchError(ApplicationError):
    """Raised when an item/adjustment currency does not match the bill (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="CURRENCY_MISMATCH",
            message="Currency của món/điều chỉnh không khớp với hóa đơn.",
        )


class NegativeTotalError(ApplicationError):
    """Raised when adjustments would drive the bill total below zero (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="NEGATIVE_TOTAL",
            message="Tổng tiền hóa đơn không thể âm.",
        )


class FoodItemMissingPriceError(ApplicationError):
    """Raised when adding a food item that has no price/currency set (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="FOOD_ITEM_MISSING_PRICE",
            message="Món ăn chưa có giá nên không thể thêm vào hóa đơn.",
        )


class InvalidQuantityError(ApplicationError):
    """Raised when a bill item quantity is not a positive integer (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_QUANTITY",
            message="Số lượng món phải lớn hơn 0.",
        )