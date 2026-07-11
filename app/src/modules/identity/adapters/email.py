"""Email delivery port + implementations.

The active provider is selected by ``EMAIL_PROVIDER`` (``core/config.py``):

- ``console`` (default, dev/test): logs the magic link at INFO, never raises.
- ``resend`` (production): calls the Resend transactional API and raises
  ``EmailDeliveryError`` on failure, which the service maps to
  ``503 EMAIL_SERVICE_UNAVAILABLE``.
- ``gmail_smtp``: sends via Gmail SMTP using an App Password (no domain
  ownership required). Uses stdlib ``smtplib`` — no extra dependency.

The service only sees the ``EmailSender`` protocol, so swapping providers needs
no service change. ``doc/ai/architecture.md`` lists the email adapter as the
planned provider integration for the Magic Link flow.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Đăng nhập MenuScan</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:36px 40px;text-align:center;">
              <div style="display:inline-flex;align-items:center;gap:10px;">
                <span style="font-size:28px;">🍽️</span>
                <span style="color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px;">MenuScan</span>
              </div>
              <p style="color:rgba(255,255,255,0.65);font-size:13px;margin:8px 0 0 0;letter-spacing:0.3px;">Số hoá thực đơn thông minh</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px 40px;">
              <h1 style="margin:0 0 8px 0;font-size:22px;font-weight:700;color:#1a1a2e;line-height:1.3;">
                Liên kết đăng nhập của bạn
              </h1>
              <p style="margin:0 0 28px 0;font-size:15px;color:#6b7280;line-height:1.6;">
                Xin chào! Nhấn nút bên dưới để đăng nhập vào MenuScan. Không cần mật khẩu.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 0 28px 0;">
                <tr>
                  <td style="border-radius:10px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);">
                    <a href="{magic_link_url}"
                       style="display:inline-block;padding:14px 36px;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;letter-spacing:0.3px;border-radius:10px;">
                      ✨ &nbsp;Đăng nhập ngay
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Warning box -->
              <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
                <tr>
                  <td style="background:#fef9ec;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;">
                    <p style="margin:0;font-size:13px;color:#92400e;line-height:1.5;">
                      ⏱️ &nbsp;<strong>Liên kết có hiệu lực trong 15 phút</strong> và chỉ dùng được một lần.
                      Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
                Nút không hoạt động? Sao chép liên kết dưới đây vào trình duyệt:<br/>
                <a href="{magic_link_url}" style="color:#667eea;word-break:break-all;font-size:11px;">{magic_link_url}</a>
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #f0f0f0;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 32px 40px;text-align:center;">
              <p style="margin:0 0 6px 0;font-size:12px;color:#9ca3af;">
                Email này được gửi tự động từ <strong>MenuScan</strong>. Vui lòng không trả lời.
              </p>
              <p style="margin:0;font-size:11px;color:#d1d5db;">
                © 2025 MenuScan · Số hoá thực đơn nhà hàng
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _magic_link_text(magic_link_url: str) -> str:
    return (
        "MENUSCAN — Liên kết đăng nhập\n"
        "=" * 40 + "\n\n"
        "Nhấn vào liên kết dưới đây để đăng nhập vào MenuScan.\n"
        "Liên kết có hiệu lực 15 phút và chỉ dùng được một lần.\n\n"
        f"  {magic_link_url}\n\n"
        "Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.\n\n"
        "---\n"
        "Email tự động từ MenuScan. Vui lòng không trả lời.\n"
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


class GmailSmtpEmailSender:
    """Production sender via Gmail SMTP with an App Password.

    Requires a Google App Password (not the account password). The password
    is never logged; only a coarse failure reason reaches the log.

    SMTP settings: smtp.gmail.com:587 with STARTTLS.
    """

    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(
        self,
        *,
        username: str,
        app_password: str,
        from_address: str,
        timeout_seconds: float,
    ) -> None:
        self._username = username
        self._app_password = app_password
        self._from_address = from_address
        self._timeout = timeout_seconds

    def send_magic_link(self, *, to_email: str, magic_link_url: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = MAGIC_LINK_SUBJECT
        msg["From"] = self._from_address
        msg["To"] = to_email
        msg.attach(MIMEText(_magic_link_text(magic_link_url), "plain", "utf-8"))
        msg.attach(MIMEText(_magic_link_html(magic_link_url), "html", "utf-8"))

        try:
            with smtplib.SMTP(
                self.SMTP_HOST, self.SMTP_PORT, timeout=self._timeout
            ) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self._username, self._app_password)
                server.sendmail(self._from_address, [to_email], msg.as_string())
        except smtplib.SMTPAuthenticationError as error:
            raise EmailDeliveryError("gmail smtp authentication failed") from error
        except smtplib.SMTPException as error:
            raise EmailDeliveryError("gmail smtp delivery failed") from error
        except OSError as error:
            raise EmailDeliveryError("gmail smtp connection failed") from error


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
