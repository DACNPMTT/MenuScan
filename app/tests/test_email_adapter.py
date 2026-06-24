"""Tests for the email adapter: ResendEmailSender (mocked HTTP) and the
``get_email_sender`` factory provider selection. No network is touched.
"""

from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from src.core.config import EmailConfig, Settings
from src.modules.identity import dependencies as deps
from src.modules.identity.adapters.email import (
    ConsoleEmailSender,
    EmailDeliveryError,
    ResendEmailSender,
)


def _console_settings() -> Settings:
    return Settings(
        database_url="postgresql://unused",
        magic_link_base_url="http://localhost:5173",
        app_env="test",
        log_level="WARNING",
        api_v1_prefix="/api/v1",
        cors_origins=("http://localhost:5173",),
        email=EmailConfig(
            provider="console",
            from_address="",
            api_key=None,
            api_base_url="https://api.resend.com",
            timeout_seconds=10.0,
        ),
    )


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _RecordingPost:
    """Records every call and returns a configurable status code."""

    def __init__(self, *, status_code: int = 200) -> None:
        self.calls: list[dict[str, object]] = []
        self._status_code = status_code

    def __call__(self, url, *, headers, json, timeout) -> _FakeResponse:  # noqa: ANN001
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return _FakeResponse(self._status_code)


def _make_resend_sender(post) -> ResendEmailSender:
    return ResendEmailSender(
        api_key="rk_test_key",
        from_address="MenuScan <noreply@example.com>",
        api_base_url="https://api.resend.com",
        timeout_seconds=10.0,
        post=post,
    )


def test_resend_sender_posts_correct_payload_on_success() -> None:
    post = _RecordingPost(status_code=200)
    sender = _make_resend_sender(post)

    sender.send_magic_link(
        to_email="user@example.com",
        magic_link_url="http://localhost:5173/auth/verify?token=abc",
    )

    assert len(post.calls) == 1
    call = post.calls[0]
    assert call["url"] == "https://api.resend.com/emails"
    assert call["headers"]["Authorization"] == "Bearer rk_test_key"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["json"]["from"] == "MenuScan <noreply@example.com>"
    assert call["json"]["to"] == ["user@example.com"]
    assert "token=abc" in call["json"]["html"]
    assert "token=abc" in call["json"]["text"]
    assert call["timeout"] == 10.0


def test_resend_sender_raises_on_http_error() -> None:
    def raising_post(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    sender = _make_resend_sender(raising_post)

    with pytest.raises(EmailDeliveryError):
        sender.send_magic_link(
            to_email="user@example.com",
            magic_link_url="http://localhost:5173/auth/verify?token=t",
        )


def test_resend_sender_raises_on_error_status() -> None:
    post = _RecordingPost(status_code=422)
    sender = _make_resend_sender(post)

    with pytest.raises(EmailDeliveryError):
        sender.send_magic_link(
            to_email="user@example.com",
            magic_link_url="http://localhost:5173/auth/verify?token=t",
        )


def test_factory_returns_console_when_provider_is_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(deps, "settings", _console_settings())
    deps.get_email_sender.cache_clear()
    try:
        assert isinstance(deps.get_email_sender(), ConsoleEmailSender)
    finally:
        deps.get_email_sender.cache_clear()


def test_factory_returns_resend_when_provider_is_resend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resend_settings = replace(
        _console_settings(),
        email=EmailConfig(
            provider="resend",
            from_address="MenuScan <noreply@example.com>",
            api_key="rk_test_key",
            api_base_url="https://api.resend.com",
            timeout_seconds=10.0,
        ),
    )
    monkeypatch.setattr(deps, "settings", resend_settings)
    deps.get_email_sender.cache_clear()
    try:
        assert isinstance(deps.get_email_sender(), ResendEmailSender)
    finally:
        deps.get_email_sender.cache_clear()
