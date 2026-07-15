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
    # URL-encoded SVG for the logo
    logo_svg = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 250' width='30' height='30'%3E"
        "%3Cg transform='translate(100, 140)'%3E"
        "%3Cpath d='M 0 -85 L 15 -95 L 35 -80 L 50 -90 L 65 -70 L 85 -65 L 75 -45 L 95 -30 L 80 -10 L 100 10 L 85 30 L 95 50 L 75 65 L 85 85 L 50 85 L 40 100 L 20 90 L 0 105 L -20 90 L -40 100 L -50 85 L -85 85 L -75 65 L -95 50 L -85 30 L -100 10 L -80 -10 L -95 -30 L -75 -45 L -85 -65 L -65 -70 L -50 -90 L -35 -80 L -15 -95 Z' fill='%2389b653' stroke='%234d6f21' stroke-width='3' stroke-linejoin='round' /%3E"
        "%3Cellipse cx='0' cy='10' rx='65' ry='75' fill='%23fde368' stroke='%23d5b035' stroke-width='2' /%3E"
        "%3C/g%3E"
        "%3Cg transform='translate(100, 135)'%3E"
        "%3Ccircle cx='-35' cy='15' r='9' fill='%23f4a6c0' opacity='0.8' /%3E"
        "%3Ccircle cx='35' cy='15' r='9' fill='%23f4a6c0' opacity='0.8' /%3E"
        "%3Cpath d='M -22 -5 Q -15 -13 -8 -5' stroke='%23222' stroke-width='4' fill='none' stroke-linecap='round' /%3E"
        "%3Cpath d='M 8 -5 Q 15 -13 22 -5' stroke='%23222' stroke-width='4' fill='none' stroke-linecap='round' /%3E"
        "%3Cpath d='M -15 5 Q 0 35 15 5 Z' fill='%23c1432e' stroke='%23222' stroke-width='2.5' stroke-linejoin='round' /%3E"
        "%3Cpath d='M -8 15 Q 0 25 8 15 Z' fill='%23ffb6c1' /%3E"
        "%3C/g%3E"
        "%3Cg transform='translate(100, 55)'%3E"
        "%3Cellipse cx='0' cy='35' rx='90' ry='15' fill='%23c8a156' /%3E"
        "%3Cpath d='M 0 -55 L -95 35 Q 0 55 95 35 Z' fill='%23eed9a1' stroke='%23a57f36' stroke-width='2' stroke-linejoin='round' /%3E"
        "%3Cpath d='M -18 -38 Q 0 -35 18 -38' stroke='%23a57f36' stroke-width='1.5' fill='none' opacity='0.4' /%3E"
        "%3Cpath d='M -36 -15 Q 0 -10 36 -15' stroke='%23a57f36' stroke-width='1.5' fill='none' opacity='0.4' /%3E"
        "%3Cpath d='M -54 8 Q 0 15 54 8' stroke='%23a57f36' stroke-width='1.5' fill='none' opacity='0.4' /%3E"
        "%3Cpath d='M -72 25 Q 0 35 72 25' stroke='%23a57f36' stroke-width='1.5' fill='none' opacity='0.4' /%3E"
        "%3C/g%3E"
        "%3C/svg%3E"
    )

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
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:24px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.06);">

          <!-- Header -->
          <tr>
            <td style="padding:40px 40px 0 40px;text-align:center;">
              <div style="display:inline-flex;align-items:center;justify-content:center;width:60px;height:60px;border-radius:16px;background-color:#f59e0b;box-shadow:0 4px 12px rgba(245,158,11,0.3);margin-bottom:16px;">
                <img src="{logo_svg}" alt="MenuScan Logo" style="display:block;width:40px;height:40px;" />
              </div>
              <h1 style="margin:0;font-size:26px;font-weight:800;color:#042c60;letter-spacing:-0.5px;">MenuScan</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px 32px 40px;text-align:center;">
              <p style="margin:0 0 8px 0;font-size:18px;font-weight:700;color:#042c60;">
                Liên kết đăng nhập của bạn
              </p>
              <p style="margin:0 0 32px 0;font-size:15px;color:#777777;line-height:1.6;">
                Xin chào! Nhấn nút bên dưới để đăng nhập vào tài khoản của bạn trên MenuScan.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 auto 32px auto;">
                <tr>
                  <td style="border-radius:14px;background-color:#58cc02;box-shadow:0 4px 0 #58a700;">
                    <a href="{magic_link_url}"
                       style="display:inline-block;padding:14px 40px;color:#ffffff;font-size:16px;font-weight:800;text-decoration:none;letter-spacing:0.3px;border-radius:14px;">
                      Đăng nhập ngay
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Thank you note -->
              <p style="margin:0 0 24px 0;font-size:15px;color:#042c60;font-weight:600;line-height:1.6;">
                Cảm ơn bạn đã tin tưởng và sử dụng MenuScan! ❤️
              </p>

              <!-- Warning box -->
              <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;text-align:left;">
                <tr>
                  <td style="background:#f7f7f7;border-radius:12px;padding:16px;">
                    <p style="margin:0;font-size:13px;color:#777777;line-height:1.5;">
                      ⏱️ <strong>Liên kết có hiệu lực trong 15 phút</strong> và chỉ dùng được một lần.
                      Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:0;font-size:12px;color:#777777;line-height:1.6;text-align:left;">
                Nút không hoạt động? Sao chép liên kết dưới đây vào trình duyệt:<br/>
                <a href="{magic_link_url}" style="color:#58cc02;word-break:break-all;font-size:11px;">{magic_link_url}</a>
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
              <p style="margin:0 0 6px 0;font-size:12px;color:#777777;">
                Email này được gửi tự động từ <strong>MenuScan</strong>. Vui lòng không trả lời.
              </p>
              <p style="margin:0;font-size:11px;color:#d1d5db;">
                © 2026 MenuScan · Số hoá thực đơn nhà hàng
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
