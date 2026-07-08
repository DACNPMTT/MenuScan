"""HTTP contract tests for ``POST /api/v1/auth/magic-links``.

Uses ``TestClient`` with the real ``api_router`` (so validation + error mapping +
router mounting are exercised) but overrides ``get_magic_link_service`` with a
stub. Business logic is covered by ``test_magic_link_service.py``; this layer
asserts the HTTP contract only.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.identity.dependencies import get_magic_link_service
from src.modules.identity.exceptions import (
    EmailServiceUnavailableError,
    MagicLinkRateLimitedError,
)
from src.modules.identity.schemas import MagicLinkData
from src.modules.identity.service import MAGIC_LINK_SUCCESS_MESSAGE


def _settings() -> Settings:
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
        storage=StorageConfig(
            provider="local",
            local_root="storage/objects",
            bucket_name=None,
            endpoint_url=None,
            region="us-east-1",
            access_key_id=None,
            secret_access_key=None,
            session_token=None,
            signed_url_seconds=300,
        ),
    )


class StubMagicLinkService:
    """Records the normalized email; returns or raises as configured."""

    def __init__(
        self,
        *,
        effect: Callable[[str], MagicLinkData] | None = None,
    ) -> None:
        self.received_emails: list[str] = []
        self._effect = effect

    def request_magic_link(self, email: str) -> MagicLinkData:
        self.received_emails.append(email)
        if self._effect is not None:
            return self._effect(email)
        return MagicLinkData(
            message=MAGIC_LINK_SUCCESS_MESSAGE,
            resend_after_seconds=60,
        )


def _make_client(stub: StubMagicLinkService) -> TestClient:
    app = create_app(
        application_settings=_settings(),
        database_engine=Mock(),
    )
    app.dependency_overrides[get_magic_link_service] = lambda: stub
    return TestClient(app, raise_server_exceptions=False)


def test_valid_email_returns_202_standard_envelope():
    stub = StubMagicLinkService()
    client = _make_client(stub)

    response = client.post(
        "/api/v1/auth/magic-links",
        json={"email": "user@example.com"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["meta"] is None
    assert body["data"]["message"] == MAGIC_LINK_SUCCESS_MESSAGE
    assert body["data"]["resend_after_seconds"] == 60


def test_invalid_email_returns_validation_error():
    stub = StubMagicLinkService()
    client = _make_client(stub)

    response = client.post(
        "/api/v1/auth/magic-links",
        json={"email": "not-an-email"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in body["error"]["details"]["fields"]
    # Invalid email never reached the service.
    assert stub.received_emails == []


def test_email_is_normalized_before_service():
    stub = StubMagicLinkService()
    client = _make_client(stub)

    response = client.post(
        "/api/v1/auth/magic-links",
        json={"email": " User@Example.com "},
    )

    assert response.status_code == 202
    assert stub.received_emails == ["user@example.com"]


def test_rate_limited_returns_429():
    def always_rate_limited(_email: str) -> MagicLinkData:
        raise MagicLinkRateLimitedError(resend_after_seconds=60)

    stub = StubMagicLinkService(effect=always_rate_limited)
    client = _make_client(stub)

    response = client.post(
        "/api/v1/auth/magic-links",
        json={"email": "user@example.com"},
    )

    assert response.status_code == 429
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RATE_LIMITED"
    assert body["error"]["details"]["resend_after_seconds"] == 60


def test_email_service_failure_returns_503():
    def always_failing(_email: str) -> MagicLinkData:
        raise EmailServiceUnavailableError()

    stub = StubMagicLinkService(effect=always_failing)
    client = _make_client(stub)

    response = client.post(
        "/api/v1/auth/magic-links",
        json={"email": "user@example.com"},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMAIL_SERVICE_UNAVAILABLE"


def test_response_does_not_reveal_account_existence():
    stub = StubMagicLinkService()
    client = _make_client(stub)

    registered = client.post(
        "/api/v1/auth/magic-links",
        json={"email": f"registered-{uuid.uuid4()}@example.com"},
    )
    unregistered = client.post(
        "/api/v1/auth/magic-links",
        json={"email": f"new-{uuid.uuid4()}@example.com"},
    )

    assert registered.status_code == 202
    assert unregistered.status_code == 202
    assert registered.json() == unregistered.json()
    body = registered.json()
    # No account-existence surface in the payload.
    for key in ("user", "exists", "registered", "user_id"):
        assert key not in body["data"]
