"""Identity-module application errors.

Both extend ``core.errors.ApplicationError`` and are auto-mapped to the standard
error envelope by ``application_error_handler``. Codes match
``doc/content/api-endpoints.md``.
"""

from __future__ import annotations

from src.core.errors import ApplicationError

RESEND_COOLDOWN_SECONDS = 60


class MagicLinkRateLimitedError(ApplicationError):
    """Raised when a resend is requested within the cooldown window (429)."""

    def __init__(self, *, resend_after_seconds: int = RESEND_COOLDOWN_SECONDS) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMITED",
            message="Vui lòng đợi trước khi yêu cầu gửi lại liên kết.",
            details={"resend_after_seconds": resend_after_seconds},
        )


class EmailServiceUnavailableError(ApplicationError):
    """Raised when the email provider cannot deliver the message (503)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="EMAIL_SERVICE_UNAVAILABLE",
            message="Dịch vụ email tạm thời không khả dụng. Vui lòng thử lại sau.",
        )
