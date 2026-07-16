"""Contract tests for POST /advisor/chat.

No DB: the advisor service, the current-user dependency and the throttle are all
overridden, so these exercise routing + auth + error mapping only.
"""

from __future__ import annotations

import uuid
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.core.rate_limit import RateLimitError, enforce_chat_throttle
from src.modules.advisor.dependencies import get_advisor_service
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

_MENU_ID = str(uuid.uuid4())


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


def _stub_user() -> User:
    return User(id=uuid.uuid4(), email="user@example.com", preferred_language="vi")


class _StubAdvisor:
    def __init__(self, answer: str = "Món này thường có vị ngọt.") -> None:
        self.answer = answer

    def chat(self, **_kwargs: object) -> str:
        return self.answer


def _make_client(*, authenticated: bool = True, throttled: bool = False) -> TestClient:
    app = create_app(application_settings=_settings(), database_engine=Mock())
    app.dependency_overrides[get_advisor_service] = lambda: _StubAdvisor()
    if authenticated:
        app.dependency_overrides[get_current_user] = _stub_user
    if throttled:

        def _raise_throttled() -> None:
            raise RateLimitError(retry_after=5)

        app.dependency_overrides[enforce_chat_throttle] = _raise_throttled
    else:
        app.dependency_overrides[enforce_chat_throttle] = lambda: None
    return TestClient(app, raise_server_exceptions=False)


def _post(client: TestClient) -> object:
    return client.post(
        "/api/v1/advisor/chat",
        json={"menu_id": _MENU_ID, "question": "Món này có ngọt không?"},
    )


def test_chat_returns_answer_envelope() -> None:
    response = _post(_make_client())
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["answer"] == "Món này thường có vị ngọt."


def test_chat_requires_login() -> None:
    response = _post(_make_client(authenticated=False))
    assert response.status_code == 401


def test_chat_throttled_returns_429() -> None:
    response = _post(_make_client(throttled=True))
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_chat_rejects_missing_question() -> None:
    client = _make_client()
    response = client.post("/api/v1/advisor/chat", json={"menu_id": _MENU_ID})
    assert response.status_code in {400, 422}


def test_chat_accepts_focus_dishes() -> None:
    client = _make_client()
    response = client.post(
        "/api/v1/advisor/chat",
        json={
            "menu_id": _MENU_ID,
            "question": "Món nào ngọt?",
            "focus_dishes": ["Chop Suey with Shrimp", "Chè đậu"],
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
