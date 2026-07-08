"""Email delivery port + implementations.

The active provider is selected by ``EMAIL_PROVIDER`` (``core/config.py``):

- ``console`` (default, dev/test): logs the magic link at INFO, never raises.
- ``resend`` (production): calls the Resend transactional API and raises
  ``EmailDeliveryError`` on failure, which the service maps to
  ``503 EMAIL_SERVICE_UNAVAILABLE``.

The service only sees the ``EmailSender`` protocol, so swapping providers needs
no service change. ``doc/ai/architecture.md`` lists the email adapter as the
planned provider integration for the Magic Link flow.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)

RESEND_EMAILS_PATH = "/emails"
MAGIC_LINK_SUBJECT = "Liên kết đăng nhập MenuScan"


class EmailDeliveryError(Exception):
    """Raised by an ``EmailSender`` when delivery fails."""


# A thin callable seam over ``httpx.post`` so the Resend sender is unit-testable
# without touching the network (tests inject a fake ``post``).
PostFn = Callable[..., httpx.Response]


@runtime_checkable
class EmailSender(Protocol):
    """Synchronous port for sending transactional email."""

    def send_magic_link(self, *, to_email: str, magic_link_url: str) -> None:
        """Send a magic-login link. Raise ``EmailDeliveryError`` on failure."""
        ...


def _magic_link_html(magic_link_url: str) -> str:
    return (
        "<p>Xin chào,</p>"
        "<p>Nhấn vào liên kết bên dưới để đăng nhập vào MenuScan. "
        "Liên kết có hiệu lực 15 phút và chỉ dùng được một lần.</p>"
        f'<p><a href="{magic_link_url}">Đăng nhập ngay</a></p>'
        f"<p>Hoặc sao chép liên kết: {magic_link_url}</p>"
    )


def _magic_link_text(magic_link_url: str) -> str:
    return (
        "Nhấn vào liên kết bên dưới để đăng nhập vào MenuScan. "
        "Liên kết có hiệu lực 15 phút và chỉ dùng được một lần.\n\n"
        f"{magic_link_url}"
    )


class ConsoleEmailSender:
    """Dev/test sender that logs the magic link at INFO.

    Never raises. The logged URL contains the raw token, so this is dev-only.
    """

    def send_magic_link(self, *, to_email: str, magic_link_url: str) -> None:
        logger.info(
            "magic_link_email_queued to_email=%s url=%s",
            to_email,
            magic_link_url,
        )


class ResendEmailSender:
    """Production sender backed by the Resend API (https://resend.com).

    ``post`` is an injectable seam over ``httpx.post`` for unit tests. The API
    key is never logged; only a coarse failure reason reaches the log.
    """

    def __init__(
        self,
        *,
        api_key: str,
        from_address: str,
        api_base_url: str,
        timeout_seconds: float,
        post: PostFn | None = None,
    ) -> None:
        self._api_key = api_key
        self._from_address = from_address
        self._api_base_url = api_base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._post = post or httpx.post

    def send_magic_link(self, *, to_email: str, magic_link_url: str) -> None:
        payload = {
            "from": self._from_address,
            "to": [to_email],
            "subject": MAGIC_LINK_SUBJECT,
            "html": _magic_link_html(magic_link_url),
            "text": _magic_link_text(magic_link_url),
        }
        try:
            response = self._post(
                f"{self._api_base_url}{RESEND_EMAILS_PATH}",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout,
            )
        except httpx.HTTPError as error:
            raise EmailDeliveryError("resend request failed") from error

        if response.status_code >= 400:
            raise EmailDeliveryError(
                f"resend rejected delivery: status={response.status_code}"
            )
