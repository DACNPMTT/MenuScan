"""Dining-session application errors."""

from __future__ import annotations

from src.core.errors import ApplicationError


class DiningSessionNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="DINING_SESSION_NOT_FOUND",
            message="Không tìm thấy phiên ăn uống.",
        )


class DiningInviteInvalidError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="DINING_INVITE_INVALID",
            message="Mã mời không hợp lệ hoặc đã hết hạn.",
        )


class DiningSessionClosedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="DINING_SESSION_CLOSED",
            message="Phiên ăn uống đã đóng, không thể tham gia.",
        )


class DiningParticipantNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="DINING_PARTICIPANT_NOT_FOUND",
            message="Không tìm thấy người tham gia.",
        )
