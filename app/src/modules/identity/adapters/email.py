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
DELETE_ACCOUNT_SUBJECT = "Xác nhận xoá tài khoản MenuScan"


class EmailDeliveryError(Exception):
    """Raised by an ``EmailSender`` when delivery fails."""


# A thin callable seam over ``httpx.post`` so the Resend sender is unit-testable
# without touching the network (tests inject a fake ``post``).
PostFn = Callable[..., httpx.Response]


@runtime_checkable
class EmailSender(Protocol):
    """Synchronous port for sending transactional email."""

    def send_magic_link(self, *, to_email: str, magic_link_url: str, lang: str = "vi") -> None:
        """Send a magic-login link. Raise ``EmailDeliveryError`` on failure."""
        ...

    def send_delete_confirmation(
        self, *, to_email: str, confirm_url: str, lang: str = "vi"
    ) -> None:
        """Send a delete-account confirmation link. Raise ``EmailDeliveryError`` on failure."""
        ...


def _magic_link_html(magic_link_url: str, lang: str = "vi") -> str:
    # URL-encoded SVG for the Nón Lá mascot (MenuScan logo)
    logo_svg = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 250'%3E"
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

    if lang == "en":
        title = "Log in to MenuScan"
        brand_desc = "Smart Menu Scanner"
        h2 = "Lightning Fast Login! 🚀"
        p_desc = "Click the magic button below to enter MenuScan instantly.<br/>No passwords required!"
        btn_text = "✨ Enter App Now"
        warning = "⏱️ Remember, this magic button only works for <strong>15 minutes</strong>!"
        thanks = "Thank you for choosing MenuScan! ❤️"
        fallback_pre = "Button not working? Copy this link:<br/>"
        footer_auto = "This email was sent automatically by <strong>MenuScan</strong>. Please do not reply."
        footer_copy = "© 2026 MenuScan · Smart Menu Scanner"
    else:
        title = "Đăng nhập MenuScan"
        brand_desc = "Sổ tay thực đơn thông minh"
        h2 = "Đăng nhập thần tốc! 🚀"
        p_desc = "Nhấn vào nút ma thuật bên dưới để vào MenuScan ngay.<br/>Không cần nhớ mật khẩu đâu nha!"
        btn_text = "✨ Vào App Ngay"
        warning = "⏱️ Nhớ nhe, nút ma thuật này chỉ linh nghiệm trong <strong>15 phút</strong> thôi!"
        thanks = "Cảm ơn bạn đã tin yêu MenuScan! ❤️"
        fallback_pre = "Nếu nút hỏng, bạn copy link này nha:<br/>"
        footer_auto = "Email này được gửi tự động từ <strong>MenuScan</strong>. Vui lòng không trả lời."
        footer_copy = "© 2026 MenuScan · Sổ tay thực đơn thông minh"

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f7f7f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Nunito',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f7f7;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:32px;border:3px solid #e5e5e5;overflow:hidden;box-shadow:0 12px 0 rgba(229,229,229,1);">

          <!-- Header -->
          <tr>
            <td style="padding:48px 40px 32px 40px;text-align:center;background-color:#58cc02;border-bottom:4px solid #58a700;">
              <table cellpadding="0" cellspacing="0" style="margin:0 auto 8px auto;">
                <tr>
                  <td style="padding-right:16px;vertical-align:middle;">
                    <img src="{logo_svg}" alt="MenuScan Logo" style="display:block;width:72px;height:72px;" />
                  </td>
                  <td style="vertical-align:middle;">
                    <h1 style="margin:0;font-size:36px;font-weight:900;color:#ffffff;letter-spacing:-1px;">MenuScan</h1>
                  </td>
                </tr>
              </table>
              <p style="margin:0;font-size:18px;color:#ecfccb;font-weight:800;letter-spacing:0.5px;text-transform:uppercase;">
                {brand_desc}
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:16px 40px 32px 40px;text-align:center;">
              <h2 style="margin:0 0 16px 0;font-size:24px;font-weight:900;color:#042c60;">
                {h2}
              </h2>
              <p style="margin:0 0 32px 0;font-size:17px;color:#777777;line-height:1.6;font-weight:600;">
                {p_desc}
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 0 40px 0;width:100%;">
                <tr>
                  <td align="center">
                    <table cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="border-radius:24px;background-color:#58cc02;border-bottom:8px solid #58a700;border-left:2px solid #58cc02;border-right:2px solid #58cc02;border-top:2px solid #58cc02;">
                          <a href="{magic_link_url}"
                             style="display:inline-block;padding:20px 40px;color:#ffffff;font-size:20px;font-weight:900;text-transform:uppercase;letter-spacing:1.5px;text-decoration:none;border-radius:24px;">
                            {btn_text}
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- Warning box -->
              <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:32px;text-align:center;background-color:#f7f7f7;border:3px solid #e5e5e5;border-radius:20px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0;font-size:15px;color:#777777;line-height:1.5;font-weight:700;">
                      {warning}
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Thank you note -->
              <p style="margin:0 0 24px 0;font-size:18px;color:#042c60;font-weight:900;line-height:1.6;text-align:center;">
                {thanks}
              </p>

              <!-- Fallback link -->
              <p style="margin:0;font-size:14px;color:#777777;line-height:1.6;text-align:center;font-weight:700;">
                {fallback_pre}
                <a href="{magic_link_url}" style="color:#58cc02;word-break:break-all;font-size:13px;text-decoration:underline;">{magic_link_url}</a>
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:2px solid #e5e5e5;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 32px 40px;text-align:center;">
              <p style="margin:0 0 8px 0;font-size:13px;color:#777777;font-weight:600;">
                {footer_auto}
              </p>
              <p style="margin:0;font-size:12px;color:#a3a3a3;font-weight:600;">
                {footer_copy}
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _magic_link_text(magic_link_url: str, lang: str = "vi") -> str:
    if lang == "en":
        return (
            "Welcome to MenuScan!\n\n"
            f"Click the magic link below to securely log in:\n  {magic_link_url}\n\n"
            "This link is valid for 15 minutes and can only be used once.\n"
            "If you didn't request this, please ignore this email.\n\n"
            "---\n"
            "Automated email from MenuScan. Please do not reply.\n"
        )
    return (
        "Xin chào từ MenuScan!\n\n"
        "Nhấn vào liên kết ma thuật dưới đây để đăng nhập an toàn:\n"
        f"  {magic_link_url}\n\n"
        "Liên kết này có hiệu lực 15 phút và chỉ dùng được một lần.\n"
        "Nếu bạn không yêu cầu đăng nhập, hãy bỏ qua email này.\n\n"
        "---\n"
        "Email tự động từ MenuScan. Vui lòng không trả lời.\n"
    )


def _delete_confirm_html(confirm_url: str, lang: str = "vi") -> str:
    # URL-encoded SVG for the Crying Nón Lá mascot
    logo_svg = (
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 250'%3E"
        "%3Cg transform='translate(100, 140)'%3E"
        "%3Cpath d='M 0 -85 L 15 -95 L 35 -80 L 50 -90 L 65 -70 L 85 -65 L 75 -45 L 95 -30 L 80 -10 L 100 10 L 85 30 L 95 50 L 75 65 L 85 85 L 50 85 L 40 100 L 20 90 L 0 105 L -20 90 L -40 100 L -50 85 L -85 85 L -75 65 L -95 50 L -85 30 L -100 10 L -80 -10 L -95 -30 L -75 -45 L -85 -65 L -65 -70 L -50 -90 L -35 -80 L -15 -95 Z' fill='%2389b653' stroke='%234d6f21' stroke-width='3' stroke-linejoin='round' /%3E"
        "%3Cellipse cx='0' cy='10' rx='65' ry='75' fill='%23fde368' stroke='%23d5b035' stroke-width='2' /%3E"
        "%3C/g%3E"
        "%3Cg transform='translate(100, 135)'%3E"
        "%3Ccircle cx='-35' cy='15' r='9' fill='%23f4a6c0' opacity='0.8' /%3E"
        "%3Ccircle cx='35' cy='15' r='9' fill='%23f4a6c0' opacity='0.8' /%3E"
        "%3Cpath d='M -22 -2 Q -15 -9 -8 -2' stroke='%23222' stroke-width='4' fill='none' stroke-linecap='round' /%3E"
        "%3Cpath d='M 8 -2 Q 15 -9 22 -2' stroke='%23222' stroke-width='4' fill='none' stroke-linecap='round' /%3E"
        "%3Cpath d='M -15 2 Q -18 10 -15 15 Q -12 10 -15 2' fill='%2360a5fa' /%3E"
        "%3Ccircle cx='-15' cy='15' r='3' fill='%2360a5fa' /%3E"
        "%3Cpath d='M 15 2 Q 12 10 15 15 Q 18 10 15 2' fill='%2360a5fa' /%3E"
        "%3Ccircle cx='15' cy='15' r='3' fill='%2360a5fa' /%3E"
        "%3Cpath d='M -12 15 Q 0 5 12 15' stroke='%23222' stroke-width='3.5' fill='none' stroke-linecap='round' /%3E"
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

    if lang == "en":
        title = "Confirm Account Deletion - MenuScan"
        header = "Confirm Account Deletion"
        h2 = "I'm so sad... 🥺"
        p_desc = "Do you really want to leave? If you have decided, please click the confirm button below."
        warning_strong = "⚠️ RED ALERT!<br/>"
        warning_sub = "<span style=\"font-weight:700;color:#e11d48;\">All your data will vanish forever and cannot be recovered.</span>"
        btn_text = "🗑️ Still Delete Account"
        fallback = "⏱️ The confirmation link is only valid for <strong>15 minutes</strong>. If you change your mind, just ignore this email!"
        copy_pre = "Button not working? Just copy this link:<br/>"
        footer_auto = "This email was sent automatically by <strong>MenuScan</strong>. Please do not reply."
        footer_copy = "© 2026 MenuScan · Smart Menu Scanner"
    else:
        title = "Xác nhận xoá tài khoản MenuScan"
        header = "Xác nhận xoá tài khoản"
        h2 = "Tớ buồn lắm... 🥺"
        p_desc = "Bạn thực sự muốn rời đi sao? Nếu đã quyết định, hãy ấn nút xác nhận bên dưới nhé."
        warning_strong = "⚠️ BÁO ĐỘNG ĐỎ!<br/>"
        warning_sub = "<span style=\"font-weight:700;color:#e11d48;\">Mọi dữ liệu của bạn sẽ bốc hơi vĩnh viễn và không thể lấy lại được.</span>"
        btn_text = "🗑️ Vẫn Xoá Tài Khoản"
        fallback = "⏱️ Link xác nhận chỉ sống được <strong>15 phút</strong>. Nếu đổi ý, cứ việc bơ email này đi nha!"
        copy_pre = "Nút không bấm được? Cứ copy link này:<br/>"
        footer_auto = "Email này được gửi tự động từ <strong>MenuScan</strong>. Vui lòng không trả lời."
        footer_copy = "© 2026 MenuScan · Sổ tay thực đơn thông minh"

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f7f7f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Nunito',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f7f7;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:32px;border:3px solid #e5e5e5;overflow:hidden;box-shadow:0 12px 0 rgba(229,229,229,1);">

          <!-- Header -->
          <tr>
            <td style="padding:48px 40px 32px 40px;text-align:center;background-color:#e11d48;border-bottom:4px solid #be123c;">
              <table cellpadding="0" cellspacing="0" style="margin:0 auto 8px auto;">
                <tr>
                  <td style="padding-right:16px;vertical-align:middle;">
                    <img src="{logo_svg}" alt="Crying MenuScan Logo" style="display:block;width:72px;height:72px;" />
                  </td>
                  <td style="vertical-align:middle;">
                    <h1 style="margin:0;font-size:36px;font-weight:900;color:#ffffff;letter-spacing:-1px;">MenuScan</h1>
                  </td>
                </tr>
              </table>
              <p style="margin:0;font-size:18px;color:#ffe4e6;font-weight:800;letter-spacing:0.5px;text-transform:uppercase;">
                {header}
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px 40px;text-align:center;">
              <h2 style="margin:0 0 16px 0;font-size:26px;font-weight:900;color:#042c60;">
                {h2}
              </h2>
              <p style="margin:0 0 32px 0;font-size:17px;color:#777777;line-height:1.6;font-weight:700;">
                {p_desc}
              </p>

              <!-- Warning box -->
              <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:32px;text-align:center;background-color:#fff1f2;border:3px solid #fda4af;border-radius:20px;">
                <tr>
                  <td style="padding:20px;">
                    <p style="margin:0;font-size:15px;color:#be123c;line-height:1.6;font-weight:900;">
                      {warning_strong}{warning_sub}
                    </p>
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 0 40px 0;width:100%;">
                <tr>
                  <td align="center">
                    <table cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="border-radius:24px;background-color:#e11d48;border-bottom:8px solid #be123c;border-left:2px solid #e11d48;border-right:2px solid #e11d48;border-top:2px solid #e11d48;">
                          <a href="{confirm_url}"
                             style="display:inline-block;padding:20px 40px;color:#ffffff;font-size:18px;font-weight:900;text-transform:uppercase;letter-spacing:1px;text-decoration:none;border-radius:24px;">
                            {btn_text}
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 24px 0;font-size:15px;color:#777777;line-height:1.6;font-weight:700;">
                {fallback}
              </p>

              <!-- Fallback link -->
              <p style="margin:0;font-size:14px;color:#777777;line-height:1.6;font-weight:700;">
                {copy_pre}
                <a href="{confirm_url}" style="color:#e11d48;word-break:break-all;font-size:13px;text-decoration:underline;">{confirm_url}</a>
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:2px solid #e5e5e5;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 32px 40px;text-align:center;">
              <p style="margin:0 0 8px 0;font-size:13px;color:#777777;font-weight:600;">
                {footer_auto}
              </p>
              <p style="margin:0;font-size:12px;color:#a3a3a3;font-weight:600;">
                {footer_copy}
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _delete_confirm_text(confirm_url: str, lang: str = "vi") -> str:
    if lang == "en":
        return (
            "We received a request to delete your MenuScan account.\n\n"
            "⚠️ THIS ACTION CANNOT BE UNDONE.\n\n"
            f"  {confirm_url}\n\n"
            "This link is valid for 15 minutes and can only be used once.\n"
            "If you didn't request this, please ignore this email.\n\n"
            "---\n"
            "Automated email from MenuScan. Please do not reply.\n"
        )
    return (
        "Chúng tôi nhận được yêu cầu xoá tài khoản MenuScan của bạn.\n\n"
        "⚠️ HÀNH ĐỘNG NÀY KHÔNG THỂ HOÀN TÁC.\n\n"
        f"  {confirm_url}\n\n"
        "Liên kết có hiệu lực 15 phút và chỉ dùng được một lần.\n"
        "Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.\n\n"
        "---\n"
        "Email tự động từ MenuScan. Vui lòng không trả lời.\n"
    )


class ConsoleEmailSender:
    """Dev/test sender that logs the magic link at INFO.

    Never raises. The logged URL contains the raw token, so this is dev-only.
    """

    def send_magic_link(self, *, to_email: str, magic_link_url: str, lang: str = "vi") -> None:
        logger.info(
            "magic_link_email_queued to_email=%s url=%s lang=%s",
            to_email,
            magic_link_url,
            lang,
        )

    def send_delete_confirmation(
        self, *, to_email: str, confirm_url: str, lang: str = "vi"
    ) -> None:
        logger.info(
            "delete_confirmation_email_queued to_email=%s url=%s",
            to_email,
            confirm_url,
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

    def send_magic_link(self, *, to_email: str, magic_link_url: str, lang: str = "vi") -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = MAGIC_LINK_SUBJECT if lang == "vi" else "MenuScan Login Link"
        msg["From"] = self._from_address
        msg["To"] = to_email
        msg.attach(MIMEText(_magic_link_text(magic_link_url, lang=lang), "plain", "utf-8"))
        msg.attach(MIMEText(_magic_link_html(magic_link_url, lang=lang), "html", "utf-8"))
        self._send_smtp(msg, to_email)

    def send_delete_confirmation(
        self, *, to_email: str, confirm_url: str, lang: str = "vi"
    ) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = DELETE_ACCOUNT_SUBJECT if lang == "vi" else "Confirm MenuScan Account Deletion"
        msg["From"] = self._from_address
        msg["To"] = to_email
        msg.attach(MIMEText(_delete_confirm_text(confirm_url, lang=lang), "plain", "utf-8"))
        msg.attach(MIMEText(_delete_confirm_html(confirm_url, lang=lang), "html", "utf-8"))
        self._send_smtp(msg, to_email)

    def _send_smtp(self, msg: MIMEMultipart, to_email: str) -> None:
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

    def send_magic_link(self, *, to_email: str, magic_link_url: str, lang: str = "vi") -> None:
        self._send_resend(
            to_email=to_email,
            subject=MAGIC_LINK_SUBJECT if lang == "vi" else "MenuScan Login Link",
            html=_magic_link_html(magic_link_url, lang=lang),
            text=_magic_link_text(magic_link_url, lang=lang),
        )

    def send_delete_confirmation(
        self, *, to_email: str, confirm_url: str, lang: str = "vi"
    ) -> None:
        self._send_resend(
            to_email=to_email,
            subject=DELETE_ACCOUNT_SUBJECT if lang == "vi" else "Confirm MenuScan Account Deletion",
            html=_delete_confirm_html(confirm_url, lang=lang),
            text=_delete_confirm_text(confirm_url, lang=lang),
        )

    def _send_resend(
        self,
        *,
        to_email: str,
        subject: str,
        html: str,
        text: str,
    ) -> None:
        payload = {
            "from": self._from_address,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
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
