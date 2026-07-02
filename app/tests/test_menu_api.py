"""HTTP contract and service tests for menu ownership and lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.exceptions import UnauthorizedError
from src.modules.identity.models import User
from src.modules.menu.dependencies import get_menu_service
from src.modules.menu.exceptions import (
    MenuForbiddenError,
    MenuItemNotFoundError,
    MenuNotFoundError,
)
from src.modules.menu.models import FoodItem, Menu, MenuStatus
from src.modules.menu.schemas import (
    CreateMenuItemRequest,
    MenuDetailResponse,
    MenuItemResponse,
    MenuSourceResponse,
    MenuSummaryResponse,
    UpdateMenuItemRequest,
)
from src.modules.menu.service import MenuService
from src.modules.menu_scan.models import ScanSession

_MENU_ID = uuid.UUID("00000000-aaaa-bbbb-cccc-111111111111")
_ITEM_ID = uuid.UUID("00000000-aaaa-bbbb-cccc-333333333333")
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

    def confirm_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuDetailResponse:
        self.calls.append({"action": "confirm", "menu_id": menu_id, "user_id": user_id})
        if isinstance(self._effect, Exception):
            raise self._effect
        return _detail_response(menu_id)

    def list_menus(
        self,
        *,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[MenuSummaryResponse], int]:
        self.calls.append(
            {
                "action": "list",
                "user_id": user_id,
                "page": page,
                "page_size": page_size,
            }
        )
        if isinstance(self._effect, Exception):
            raise self._effect
        return [_summary_response(_MENU_ID)], 42

    def get_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuDetailResponse:
        self.calls.append({"action": "get", "menu_id": menu_id, "user_id": user_id})
        if isinstance(self._effect, Exception):
            raise self._effect
        return _detail_response(menu_id)

    def delete_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self.calls.append({"action": "delete", "menu_id": menu_id, "user_id": user_id})
        if isinstance(self._effect, Exception):
            raise self._effect

    def create_menu_item(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateMenuItemRequest,
    ) -> MenuItemResponse:
        self.calls.append(
            {
                "action": "create_item",
                "menu_id": menu_id,
                "user_id": user_id,
                "payload": payload,
            }
        )
        if isinstance(self._effect, Exception):
            raise self._effect
        return MenuItemResponse(
            id=_ITEM_ID,
            original_name=payload.original_name,
            translated_name=payload.translated_name,
            original_description=payload.original_description,
            translated_description=payload.translated_description,
            price=payload.price,
            currency=payload.currency,
            category=payload.category,
            confidence_score=None,
            sort_order=3,
        )

    def update_menu_item(
        self,
        *,
        menu_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: UpdateMenuItemRequest,
    ) -> MenuItemResponse:
        self.calls.append(
            {
                "action": "update_item",
                "menu_id": menu_id,
                "item_id": item_id,
                "user_id": user_id,
                "payload": payload,
            }
        )
        if isinstance(self._effect, Exception):
            raise self._effect
        return MenuItemResponse(
            id=item_id,
            original_name=payload.original_name or "Pho",
            translated_name=payload.translated_name,
            original_description=payload.original_description,
            translated_description=payload.translated_description,
            price=payload.price,
            currency=payload.currency,
            category=payload.category,
            confidence_score=Decimal("0.55"),
            sort_order=0,
        )

    def delete_menu_item(
        self,
        *,
        menu_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self.calls.append(
            {
                "action": "delete_item",
                "menu_id": menu_id,
                "item_id": item_id,
                "user_id": user_id,
            }
        )
        if isinstance(self._effect, Exception):
            raise self._effect


def _source_response() -> MenuSourceResponse:
    return MenuSourceResponse(
        scan_id=uuid.UUID("00000000-aaaa-bbbb-cccc-222222222222"),
        file_name="menu.png",
        mime_type="image/png",
        file_size=1234,
        preview_url="/api/v1/scans/00000000-aaaa-bbbb-cccc-222222222222/source",
    )


def _summary_response(menu_id: uuid.UUID) -> MenuSummaryResponse:
    return MenuSummaryResponse(
        id=menu_id,
        title="Lunch Menu",
        status=MenuStatus.CONFIRMED,
        is_saved=True,
        item_count=3,
        default_currency="USD",
        source=_source_response(),
        created_at=_UPDATED_AT,
        updated_at=_UPDATED_AT,
        confirmed_at=_UPDATED_AT,
    )


def _detail_response(menu_id: uuid.UUID) -> MenuDetailResponse:
    return MenuDetailResponse(
        id=menu_id,
        title="Lunch Menu",
        status=MenuStatus.CONFIRMED,
        is_saved=True,
        source_language="en",
        target_language="vi",
        default_currency="USD",
        source=_source_response(),
        items=[],
        created_at=_UPDATED_AT,
        updated_at=_UPDATED_AT,
        confirmed_at=_UPDATED_AT,
    )


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


def test_confirm_menu_returns_confirmed_detail() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.post(f"/api/v1/menus/{_MENU_ID}/confirm")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(_MENU_ID)
    assert body["data"]["status"] == "CONFIRMED"
    assert body["data"]["is_saved"] is True
    assert body["data"]["source"]["file_name"] == "menu.png"
    assert stub.calls[0]["action"] == "confirm"


def test_list_menus_returns_recent_scan_metadata_and_pagination() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.get("/api/v1/menus?page=2&page_size=10")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {
        "page": 2,
        "page_size": 10,
        "total": 42,
        "total_pages": 5,
    }
    assert body["data"][0]["item_count"] == 3
    assert body["data"][0]["source"]["preview_url"].endswith("/source")
    assert stub.calls[0]["action"] == "list"


def test_get_menu_returns_detail() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.get(f"/api/v1/menus/{_MENU_ID}")

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Lunch Menu"
    assert stub.calls[0]["action"] == "get"


def test_get_menu_forbidden_returns_403() -> None:
    stub = StubMenuService(effect=MenuForbiddenError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/menus/{_MENU_ID}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_delete_menu_returns_no_content() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.delete(f"/api/v1/menus/{_MENU_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert stub.calls[0]["action"] == "delete"


def test_create_menu_item_returns_created_item() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.post(
        f"/api/v1/menus/{_MENU_ID}/items",
        json={
            "original_name": "Extra rice",
            "price": "2.50",
            "currency": "USD",
            "category": "Manual",
            "original_description": "For sharing",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["original_name"] == "Extra rice"
    assert body["data"]["price"] == "2.50"
    assert body["data"]["currency"] == "USD"
    assert stub.calls[0]["action"] == "create_item"


def test_create_menu_item_forbidden_returns_403() -> None:
    stub = StubMenuService(effect=MenuForbiddenError())
    client = _make_client(stub)

    response = client.post(
        f"/api/v1/menus/{_MENU_ID}/items",
        json={"original_name": "Extra rice", "price": "2.50"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_update_menu_item_returns_updated_item() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}/items/{_ITEM_ID}",
        json={
            "original_name": "Pho bo",
            "translated_name": "Beef noodle soup",
            "price": "9.25",
            "currency": "USD",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(_ITEM_ID)
    assert body["data"]["original_name"] == "Pho bo"
    assert body["data"]["translated_name"] == "Beef noodle soup"
    assert body["data"]["price"] == "9.25"
    assert stub.calls[0]["action"] == "update_item"


def test_update_menu_item_not_found_returns_404() -> None:
    stub = StubMenuService(effect=MenuItemNotFoundError())
    client = _make_client(stub)

    response = client.patch(
        f"/api/v1/menus/{_MENU_ID}/items/{_ITEM_ID}",
        json={"translated_name": "Beef noodle soup"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MENU_ITEM_NOT_FOUND"


def test_delete_menu_item_returns_no_content() -> None:
    stub = StubMenuService()
    client = _make_client(stub)

    response = client.delete(f"/api/v1/menus/{_MENU_ID}/items/{_ITEM_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert stub.calls[0]["action"] == "delete_item"


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class FakeMenuRepository:
    def __init__(
        self,
        menu: Menu | None,
        *,
        list_rows: list[tuple[Menu, int]] | None = None,
        total: int = 0,
    ) -> None:
        self.menu = menu
        self.list_rows = list_rows or []
        self.total = total
        self.saved_menu: Menu | None = None
        self.saved_item: FoodItem | None = None
        self.deleted_item: FoodItem | None = None

    def get_by_id(self, session: FakeSession, *, menu_id: uuid.UUID) -> Menu | None:
        if (
            self.menu is not None
            and self.menu.id == menu_id
            and self.menu.deleted_at is None
        ):
            return self.menu
        return None

    def list_for_user(
        self,
        session: FakeSession,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> list[tuple[Menu, int]]:
        return self.list_rows[offset : offset + limit]

    def count_for_user(self, session: FakeSession, *, user_id: uuid.UUID) -> int:
        return self.total

    def save(self, session: FakeSession, menu: Menu) -> Menu:
        self.saved_menu = menu
        return menu

    def save_item(self, session: FakeSession, item: FoodItem) -> FoodItem:
        if item.id is None:
            item.id = uuid.uuid4()
        self.saved_item = item
        return item

    def delete_item(self, session: FakeSession, item: FoodItem) -> None:
        self.deleted_item = item


def _menu_for_owner(owner_id: uuid.UUID) -> Menu:
    scan = ScanSession(
        id=uuid.uuid4(),
        user_id=owner_id,
        source_object_key="users/u/scans/s/source",
        source_file_name="menu.png",
        source_mime_type="image/png",
        source_file_size=1234,
        target_language="vi",
    )
    menu = Menu(
        id=_MENU_ID,
        title="Lunch Menu",
        source_language="en",
        target_language="vi",
        default_currency="USD",
        scan_session=scan,
        is_saved=False,
        status=MenuStatus.DRAFT,
        saved_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    menu.food_items = [
        FoodItem(
            id=_ITEM_ID,
            original_name="Pho",
            translated_name=None,
            sort_order=0,
        )
    ]
    return menu


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


def test_menu_service_confirms_draft_idempotently() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    session = FakeSession()
    repository = FakeMenuRepository(menu)
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    data = service.confirm_menu(menu_id=menu.id, user_id=owner_id)

    assert data.status == MenuStatus.CONFIRMED
    assert menu.status == MenuStatus.CONFIRMED
    assert menu.is_saved is True
    assert menu.saved_at == _UPDATED_AT
    assert session.committed is True

    session.committed = False
    data = service.confirm_menu(menu_id=menu.id, user_id=owner_id)

    assert data.status == MenuStatus.CONFIRMED
    assert session.committed is False


def test_menu_service_lists_owned_menus_with_metadata() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    menu.status = MenuStatus.CONFIRMED
    menu.is_saved = True
    menu.saved_at = _UPDATED_AT
    repository = FakeMenuRepository(menu, list_rows=[(menu, 1)], total=1)
    service = MenuService(
        session=FakeSession(),  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    items, total = service.list_menus(user_id=owner_id, page=1, page_size=20)

    assert total == 1
    assert items[0].id == menu.id
    assert items[0].item_count == 1
    assert items[0].source.file_name == "menu.png"


def test_menu_service_delete_soft_deletes_menu_and_source_scan() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    session = FakeSession()
    repository = FakeMenuRepository(menu)
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    service.delete_menu(menu_id=menu.id, user_id=owner_id)

    assert menu.deleted_at == _UPDATED_AT
    assert menu.scan_session.deleted_at == _UPDATED_AT
    assert menu.food_items != []
    assert repository.saved_menu is menu
    assert session.committed is True


def test_menu_service_creates_owned_menu_item_with_next_sort_order() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    session = FakeSession()
    repository = FakeMenuRepository(menu)
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    item = service.create_menu_item(
        menu_id=menu.id,
        user_id=owner_id,
        payload=CreateMenuItemRequest(
            original_name=" Extra rice ",
            price=Decimal("2.50"),
            currency="usd",
            category=" Manual ",
        ),
    )

    assert item.original_name == "Extra rice"
    assert item.price == Decimal("2.50")
    assert item.currency == "USD"
    assert item.category == "Manual"
    assert item.sort_order == 1
    assert repository.saved_item is not None
    assert repository.saved_item.menu_id == menu.id
    assert repository.saved_menu is menu
    assert menu.updated_at == _UPDATED_AT
    assert session.committed is True


def test_menu_service_updates_owned_menu_item() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    session = FakeSession()
    repository = FakeMenuRepository(menu)
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    item = service.update_menu_item(
        menu_id=menu.id,
        item_id=_ITEM_ID,
        user_id=owner_id,
        payload=UpdateMenuItemRequest(
            original_name=" Pho bo ",
            translated_name=" Beef noodle soup ",
            price=Decimal("9.25"),
            currency="usd",
        ),
    )

    assert item.original_name == "Pho bo"
    assert item.translated_name == "Beef noodle soup"
    assert item.price == Decimal("9.25")
    assert item.currency == "USD"
    assert repository.saved_item is menu.food_items[0]
    assert repository.saved_menu is menu
    assert menu.updated_at == _UPDATED_AT
    assert session.committed is True


def test_menu_service_deletes_owned_menu_item() -> None:
    owner_id = uuid.uuid4()
    menu = _menu_for_owner(owner_id)
    session = FakeSession()
    repository = FakeMenuRepository(menu)
    service = MenuService(
        session=session,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        clock=lambda: _UPDATED_AT,
    )

    service.delete_menu_item(menu_id=menu.id, item_id=_ITEM_ID, user_id=owner_id)

    assert repository.deleted_item is not None
    assert repository.deleted_item.id == _ITEM_ID
    assert menu.food_items == []
    assert repository.saved_menu is menu
    assert menu.updated_at == _UPDATED_AT
    assert session.committed is True
