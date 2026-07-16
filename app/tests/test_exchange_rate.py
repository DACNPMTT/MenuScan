"""Tests for the currency exchange-rate service and endpoint."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.exchange.dependencies import get_exchange_rate_service
from src.modules.exchange.service import (
    ExchangeRates,
    ExchangeRateService,
    ExchangeRateUnavailableError,
)


def _ok_body(base: str = "VND") -> dict[str, Any]:
    return {
        "result": "success",
        "base_code": base,
        "time_last_update_utc": "Sat, 05 Jul 2026 00:00:01 +0000",
        "rates": {"VND": 1, "USD": 0.000039, "EUR": 0.000036, "JPY": 0.0061},
    }


class FakeResponse:
    def __init__(
        self, status_code: int = 200, body: dict[str, Any] | None = None
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else _ok_body()

    def json(self) -> dict[str, Any]:
        return self._body


class FakeClient:
    def __init__(self, action: FakeResponse | Exception) -> None:
        self.calls: list[str] = []
        self._action = action

    def get(self, url: str) -> FakeResponse:
        self.calls.append(url)
        if isinstance(self._action, Exception):
            raise self._action
        return self._action


def _service(
    action: FakeResponse | Exception, ttl: int = 3600
) -> tuple[ExchangeRateService, FakeClient]:
    client = FakeClient(action)
    service = ExchangeRateService(
        api_base_url="https://rates.example.test/v6",
        timeout_seconds=5,
        cache_ttl_seconds=ttl,
        client=client,  # type: ignore[arg-type]
    )
    return service, client


def test_get_rates_returns_parsed_rates() -> None:
    service, client = _service(FakeResponse())

    rates = service.get_rates("vnd")

    assert client.calls == ["https://rates.example.test/v6/latest/VND"]
    assert rates.base == "VND"
    assert rates.rates["USD"] == 0.000039
    assert rates.updated_at is not None


def test_get_rates_caches_within_ttl() -> None:
    service, client = _service(FakeResponse())

    service.get_rates("VND")
    service.get_rates("VND")

    assert len(client.calls) == 1  # second call served from cache


def test_get_rates_refetches_when_ttl_zero() -> None:
    service, client = _service(FakeResponse(), ttl=0)

    service.get_rates("VND")
    service.get_rates("VND")

    assert len(client.calls) == 2


def test_provider_http_error_raises_unavailable() -> None:
    service, _ = _service(httpx.ConnectError("boom"))
    with pytest.raises(ExchangeRateUnavailableError):
        service.get_rates("VND")


def test_provider_error_result_raises_unavailable() -> None:
    service, _ = _service(FakeResponse(200, {"result": "error"}))
    with pytest.raises(ExchangeRateUnavailableError):
        service.get_rates("VND")


def test_provider_non_200_raises_unavailable() -> None:
    service, _ = _service(FakeResponse(500, {}))
    with pytest.raises(ExchangeRateUnavailableError):
        service.get_rates("VND")


# --- Endpoint -------------------------------------------------------------


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


class _StubService:
    def __init__(self, rates: ExchangeRates | Exception) -> None:
        self._rates = rates

    def get_rates(self, base: str) -> ExchangeRates:
        if isinstance(self._rates, Exception):
            raise self._rates
        return self._rates


def _client(stub: _StubService) -> TestClient:
    from unittest.mock import Mock

    app = create_app(application_settings=_settings(), database_engine=Mock())
    app.dependency_overrides[get_exchange_rate_service] = lambda: stub
    return TestClient(app, raise_server_exceptions=False)


def test_endpoint_returns_rates_envelope() -> None:
    stub = _StubService(
        ExchangeRates(base="VND", rates={"USD": 0.000039}, updated_at="now")
    )
    client = _client(stub)

    resp = client.get("/api/v1/exchange-rates", params={"base": "VND"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["base"] == "VND"
    assert body["data"]["rates"]["USD"] == 0.000039


def test_endpoint_maps_provider_failure_to_503() -> None:
    stub = _StubService(ExchangeRateUnavailableError("down"))
    client = _client(stub)

    resp = client.get("/api/v1/exchange-rates", params={"base": "VND"})

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
