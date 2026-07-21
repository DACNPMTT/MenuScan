"""feed_recommend application errors.

Mirrors the identity module pattern: each error declares its own HTTP status
code, stable ``code`` string, and user-facing message.
"""

from __future__ import annotations

from src.core.errors import ApplicationError


class LocationNotSetError(ApplicationError):
    """Raised when the diner opens the feed before setting a location (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="LOCATION_NOT_SET",
            message="Vui lòng chia sẻ vị trí hoặc chọn thành phố để xem feed.",
        )


class RestaurantNotFoundError(ApplicationError):
    """Raised when a ``restaurant_source_id`` does not exist in the cache (404)."""

    def __init__(self, source_id: int | None = None) -> None:
        suffix = f" (id={source_id})" if source_id is not None else ""
        super().__init__(
            status_code=404,
            code="RESTAURANT_NOT_FOUND",
            message=f"Không tìm thấy quán ăn{suffix}.",
        )


class AlreadySavedError(ApplicationError):
    """Raised when the diner tries to save a restaurant they already saved (409)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="RESTAURANT_ALREADY_SAVED",
            message="Bạn đã lưu quán này rồi.",
        )
