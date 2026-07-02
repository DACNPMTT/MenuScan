"""HTTP contract and service tests for menu saved-state updates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.exceptions import UnauthorizedError
from src.modules.identity.models import User
from src.modules.menu.dependencies import get_menu_service
from src.modules.menu.exceptions import MenuForbiddenError, MenuNotFoundError
from src.modules.menu.models import Menu
from src.modules.menu.service import MenuService
from src.modules.menu_scan.models import ScanSession

_MENU_ID = uuid.UUID("00000000-aaaa-bbbb-cccc-111111111111")
_UPDATED_AT = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)


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


def _stub_user(*, user_id: uuid.UUID | None = None) -> User:
    return User(
        id=user_id or uuid.uuid4(),
        email="user@example.com",
        preferred_language="vi",
    )


class StubMenuService:
    def __init__(self, *, effect: Menu | Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._effect = effect

    def update_saved_state(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
        is_saved: bool,
    ) -> Menu:
        self.calls.append(
            {
                "menu_id": menu_id,
                "user_id": user_id,
                "is_saved": is_saved,
            }
        )
        if isinstance(self._effect, Exception):
            raise self._effect
        if self._effect is not None:
            return self._effect
        return Menu(id=menu_id, is_saved=is_saved, updated_at=_UPDATED_AT)


def _make_client(
    stub: StubMenuService,
    *,
    authenticated: bool = True,
) -> TestClient:
    user = _stub_user()
    app = create_app(
        application_settings=_settings(),
        database_engine=Mock(),
    )
    app.dependency_overrides[get_menu_service] = lambda: stub
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user
    else:
        app.dependency_overrides[get_current_user] = lambda: _raise_unauthorized()
    return TestClient(app, raise_server_exceptions=False)


def _raise_unauthorized() -> None:
    raise UnauthorizedError()


def test_patch_menu_save_returns_saved_state() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}",
        json={"is_saved": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"] is None
    assert body["data"]["id"] == str(_MENU_ID)
    assert body["data"]["is_saved"] is True
    assert body["data"]["updated_at"] == "2026-01-01T00:05:00Z"
    assert stub.calls[0]["is_saved"] is True


def test_patch_menu_unsave_returns_unsaved_state() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}",
        json={"is_saved": False},
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_saved"] is False
    assert stub.calls[0]["is_saved"] is False


def test_patch_menu_not_found_returns_404() -> None:
    stub = StubMenuService(effect=MenuNotFoundError())
    client = _make_client(stub)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}",
        json={"is_saved": True},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MENU_NOT_FOUND"


def test_patch_menu_forbidden_returns_403() -> None:
    stub = StubMenuService(effect=MenuForbiddenError())
    client = _make_client(stub)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}",
        json={"is_saved": True},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_patch_menu_requires_authentication() -> None:
    stub = StubMenuService()
    client = _make_client(stub, authenticated=False)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}",
        json={"is_saved": True},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert stub.calls == []


def test_patch_menu_requires_is_saved_field() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.patch(f"/api/v1/menus/{_MENU_ID}", json={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert stub.calls == []


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class FakeMenuRepository:
    def __init__(self, menu: Menu | None) -> None:
        self.menu = menu
        self.saved_menu: Menu | None = None

    def get_by_id(self, session: FakeSession, *, menu_id: uuid.UUID) -> Menu | None:
        return self.menu if self.menu is not None and self.menu.id == menu_id else None

    def save(self, session: FakeSession, menu: Menu) -> Menu:
        self.saved_menu = menu
        return menu


def _menu_for_owner(owner_id: uuid.UUID) -> Menu:
    scan = ScanSession(id=uuid.uuid4(), user_id=owner_id)
    return Menu(
        id=_MENU_ID,
        scan_session=scan,
        is_saved=False,
        saved_at=None,
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_menu_service_saves_menu_with_timestamps() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    session = FakeSession()
    repository = FakeMenuRepository(menu)
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    updated = service.update_saved_state(
        menu_id=menu.id,
        user_id=owner_id,
        is_saved=True,
    )

    assert updated.is_saved is True
    assert updated.saved_at == _UPDATED_AT
    assert updated.updated_at == _UPDATED_AT
    assert repository.saved_menu is menu
    assert session.committed is True


def test_menu_service_unsaves_menu_and_clears_saved_at() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    menu.is_saved = True
    menu.saved_at = _UPDATED_AT
    session = FakeSession()
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=FakeMenuRepository(menu),  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    updated = service.update_saved_state(
        menu_id=menu.id,
        user_id=owner_id,
        is_saved=False,
    )

    assert updated.is_saved is False
    assert updated.saved_at is None
    assert updated.updated_at == _UPDATED_AT
    assert session.committed is True


def test_menu_service_rejects_non_owner() -> None:
    menu = _menu_for_owner(uuid.uuid4())
    service = MenuService(
        session=FakeSession(),  # type: ignore[arg-type]
        repository=FakeMenuRepository(menu),  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    with pytest.raises(MenuForbiddenError):
        service.update_saved_state(
            menu_id=menu.id,
            user_id=uuid.uuid4(),
            is_saved=True,
        )
