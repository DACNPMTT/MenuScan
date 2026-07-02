from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.modules.menu.exceptions import MenuForbiddenError, MenuNotFoundError
from src.modules.menu.models import FoodItem, Menu, MenuStatus
from src.modules.menu.repository import MenuRepository
from src.modules.menu.schemas import (
    CreateMenuItemRequest,
    MenuDetailResponse,
    MenuItemResponse,
    MenuSourceResponse,
    MenuSummaryResponse,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MenuService:
    def __init__(
        self,
        *,
        session: Session,
        repository: MenuRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._clock = clock or _utcnow

    def update_saved_state(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
        is_saved: bool,
    ) -> Menu:
        menu = self._repository.get_by_id(self._session, menu_id=menu_id)
        if menu is None:
            raise MenuNotFoundError()
        if menu.scan_session.user_id != user_id:
            raise MenuForbiddenError()

        now = self._clock()
        menu.is_saved = is_saved
        menu.saved_at = now if is_saved else None
        menu.updated_at = now
        self._repository.save(self._session, menu)
        self._session.commit()
        return menu

    def confirm_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuDetailResponse:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        now = self._clock()
        if menu.status == MenuStatus.DRAFT:
            menu.status = MenuStatus.CONFIRMED
            menu.is_saved = True
            menu.saved_at = menu.saved_at or now
            menu.updated_at = now
            self._repository.save(self._session, menu)
            self._session.commit()
        return _menu_detail_data(menu)

    def list_menus(
        self,
        *,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[MenuSummaryResponse], int]:
        offset = (page - 1) * page_size
        rows = self._repository.list_for_user(
            self._session,
            user_id=user_id,
            limit=page_size,
            offset=offset,
        )
        total = self._repository.count_for_user(self._session, user_id=user_id)
        return [_menu_summary_data(menu, item_count) for menu, item_count in rows], total

    def get_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuDetailResponse:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        return _menu_detail_data(menu)

    def delete_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        now = self._clock()
        menu.deleted_at = now
        menu.updated_at = now
        menu.scan_session.deleted_at = now
        self._repository.save(self._session, menu)
        self._session.commit()

    def create_menu_item(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: CreateMenuItemRequest,
    ) -> MenuItemResponse:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        now = self._clock()
        next_sort_order = (
            max((item.sort_order for item in menu.food_items), default=-1) + 1
        )
        item = FoodItem(
            menu_id=menu.id,
            original_name=payload.original_name.strip(),
            translated_name=payload.translated_name.strip()
            if payload.translated_name
            else None,
            original_description=payload.original_description.strip()
            if payload.original_description
            else None,
            translated_description=payload.translated_description.strip()
            if payload.translated_description
            else None,
            price=payload.price,
            currency=payload.currency.upper() if payload.currency else None,
            category=payload.category.strip() if payload.category else None,
            sort_order=next_sort_order,
            created_at=now,
            updated_at=now,
        )
        menu.updated_at = now
        self._repository.save_item(self._session, item)
        self._repository.save(self._session, menu)
        self._session.commit()
        return MenuItemResponse.model_validate(item)

    def _get_owned_menu(self, *, menu_id: uuid.UUID, user_id: uuid.UUID) -> Menu:
        menu = self._repository.get_by_id(self._session, menu_id=menu_id)
        if menu is None:
            raise MenuNotFoundError()
        if menu.scan_session.user_id != user_id:
            raise MenuForbiddenError()
        return menu


def _menu_source_data(menu: Menu) -> MenuSourceResponse:
    scan = menu.scan_session
    return MenuSourceResponse(
        scan_id=scan.id,
        file_name=scan.source_file_name,
        mime_type=scan.source_mime_type,
        file_size=scan.source_file_size,
        preview_url=f"/api/v1/scans/{scan.id}/source",
    )


def _menu_summary_data(menu: Menu, item_count: int) -> MenuSummaryResponse:
    return MenuSummaryResponse(
        id=menu.id,
        title=menu.title,
        status=menu.status,
        is_saved=menu.is_saved,
        item_count=item_count,
        default_currency=menu.default_currency,
        source=_menu_source_data(menu),
        created_at=menu.created_at,
        updated_at=menu.updated_at,
        confirmed_at=menu.saved_at if menu.status == MenuStatus.CONFIRMED else None,
    )


def _menu_detail_data(menu: Menu) -> MenuDetailResponse:
    return MenuDetailResponse(
        id=menu.id,
        title=menu.title,
        status=menu.status,
        is_saved=menu.is_saved,
        source_language=menu.source_language,
        target_language=menu.target_language,
        default_currency=menu.default_currency,
        source=_menu_source_data(menu),
        items=[
            MenuItemResponse.model_validate(item)
            for item in sorted(menu.food_items, key=lambda item: item.sort_order)
        ],
        created_at=menu.created_at,
        updated_at=menu.updated_at,
        confirmed_at=menu.saved_at if menu.status == MenuStatus.CONFIRMED else None,
    )
