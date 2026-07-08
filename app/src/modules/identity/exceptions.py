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


class InvalidMagicLinkError(ApplicationError):
    """Raised when the magic link token is invalid or already consumed (400)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_MAGIC_LINK",
            message="Liên kết đăng nhập không hợp lệ hoặc đã được sử dụng.",
        )


class MagicLinkExpiredError(ApplicationError):
    """Raised when the magic link token has expired (401)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="MAGIC_LINK_EXPIRED",
            message="Liên kết đăng nhập đã hết hạn.",
        )


class SessionExpiredError(ApplicationError):
    """Raised when the refresh session has expired (401)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="SESSION_EXPIRED",
            message="Phiên đăng nhập đã hết hạn.",
        )


class SessionRevokedError(ApplicationError):
    """Raised when the session has been revoked (401)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="SESSION_REVOKED",
            message="Phiên đăng nhập đã bị thu hồi hoặc không hợp lệ.",
        )


class UnauthorizedError(ApplicationError):
    """Raised when access token is missing or invalid (401)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="UNAUTHORIZED",
            message="Thiếu hoặc sai token truy cập.",
        )


class InvalidCredentialsError(ApplicationError):
    """Raised when email or password is invalid during login (401)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Email hoặc mật khẩu không chính xác.",
        )
