"""Fail-fast guard: a non-dev/test deploy must not sign JWTs with the public
default secret key."""

from __future__ import annotations

import pytest

from src.core.config import DEFAULT_SECRET_KEY, Settings


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("APP_ENV", "SECRET_KEY", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)


def test_production_without_secret_key_refuses_to_boot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings.from_environment()


def test_production_with_secret_key_boots(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("SECRET_KEY", "a-real-strong-secret-value")

    settings = Settings.from_environment()
    assert settings.secret_key != DEFAULT_SECRET_KEY


@pytest.mark.parametrize("env", ["development", "test"])
def test_dev_and_test_may_use_default_secret(
    env: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    settings = Settings.from_environment()
    assert settings.secret_key == DEFAULT_SECRET_KEY
