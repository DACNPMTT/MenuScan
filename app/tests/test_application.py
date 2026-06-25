from unittest.mock import Mock

import pytest
from fastapi import APIRouter, Query
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.core import application as application_module
from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig


def _default_email_config() -> EmailConfig:
    return EmailConfig(
        provider="console",
        from_address="",
        api_key=None,
        api_base_url="https://api.resend.com",
        timeout_seconds=10.0,
    )


def _default_storage_config() -> StorageConfig:
    return StorageConfig(
        provider="local",
        local_root="storage/objects",
        bucket_name=None,
        endpoint_url=None,
        region="us-east-1",
        access_key_id=None,
        secret_access_key=None,
        session_token=None,
        signed_url_seconds=300,
    )


def make_settings(
    *,
    api_v1_prefix: str = "/api/v1",
    cors_origins: tuple[str, ...] = ("http://localhost:5173",),
    magic_link_base_url: str = "http://localhost:5173",
    email: EmailConfig | None = None,
    storage: StorageConfig | None = None,
) -> Settings:
    return Settings(
        database_url="postgresql://unused",
        magic_link_base_url=magic_link_base_url,
        app_env="test",
        log_level="WARNING",
        api_v1_prefix=api_v1_prefix,
        cors_origins=cors_origins,
        email=email or _default_email_config(),
        storage=storage or _default_storage_config(),
    )


def make_client(
    *,
    api_router: APIRouter | None = None,
    settings: Settings | None = None,
    database_engine: Mock | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            application_settings=settings or make_settings(),
            application_api_router=api_router or APIRouter(),
            database_engine=database_engine or Mock(),
        ),
        raise_server_exceptions=False,
    )


def test_module_router_is_mounted_under_configured_api_prefix() -> None:
    router = APIRouter()

    @router.get("/probe")
    def get_probe() -> dict[str, bool]:
        return {"mounted": True}

    client = make_client(
        api_router=router,
        settings=make_settings(api_v1_prefix="/custom/v1"),
    )

    response = client.get("/custom/v1/probe")

    assert response.status_code == 200
    assert response.json() == {"mounted": True}


def test_health_does_not_check_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(_: object) -> None:
        raise AssertionError("health must not check the database")

    monkeypatch.setattr(
        application_module,
        "check_database",
        fail_if_called,
    )

    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"].startswith("req_")


def test_ready_returns_database_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_check = Mock()
    monkeypatch.setattr(
        application_module,
        "check_database",
        database_check,
    )

    response = make_client().get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "email": "ok",
        "storage": "ok",
    }
    database_check.assert_called_once()


def test_ready_returns_503_when_database_is_unavailable() -> None:
    database_engine = Mock()
    database_engine.connect.side_effect = OperationalError(
        "SELECT 1",
        {},
        ConnectionError("database unavailable"),
    )

    response = make_client(database_engine=database_engine).get("/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert response.json()["error"]["details"] == {"dependency": "database"}


def test_settings_load_cors_origins_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://one.example, https://two.example",
    )

    settings = Settings.from_environment()

    assert settings.cors_origins == (
        "https://one.example",
        "https://two.example",
    )


def test_settings_reject_wildcard_cors_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="cannot contain"):
        Settings.from_environment()


def test_cors_uses_origins_from_settings() -> None:
    client = make_client(
        settings=make_settings(
            cors_origins=("https://frontend.example",),
        )
    )

    response = client.options(
        "/health",
        headers={
            "Origin": "https://frontend.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://frontend.example"
    )


def test_validation_error_uses_standard_error_contract() -> None:
    router = APIRouter()

    @router.get("/search")
    def search(query: str = Query(min_length=3)) -> dict[str, str]:
        return {"query": query}

    response = make_client(api_router=router).get(
        "/api/v1/search",
        params={"query": "a"},
    )

    body = response.json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "query.query" in body["error"]["details"]["fields"]
    assert body["error"]["request_id"].startswith("req_")


def test_not_found_uses_standard_error_contract() -> None:
    response = make_client().get("/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_internal_error_does_not_expose_exception_details() -> None:
    router = APIRouter()

    @router.get("/explode")
    def explode() -> None:
        raise RuntimeError("database password is secret")

    response = make_client(api_router=router).get("/api/v1/explode")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "database password is secret" not in response.text
    assert "Traceback" not in response.text
