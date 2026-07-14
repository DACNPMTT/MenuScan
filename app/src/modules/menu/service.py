from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.dining.models import DiningSession
from src.modules.dining.presenters import load_recommendation_view
from src.modules.dining.service import DiningSessionService
from src.modules.menu.exceptions import (
    MenuForbiddenError,
    MenuItemNotFoundError,
    MenuNotFoundError,
)
from src.modules.menu.models import FoodItem, Menu, MenuStatus
from src.modules.menu.repository import MenuRepository
from src.modules.menu.schemas import (
    CreateMenuItemRequest,
    EnrichmentStatus,
    ListMenuItemsQuery,
    MenuDetailResponse,
    MenuEnrichResponse,
    MenuItemResponse,
    MenuSourceResponse,
    MenuSummaryResponse,
    UpdateMenuItemRequest,
)
from src.modules.menu_scan.food_enricher import (
    DishInput,
    FoodEnricher,
    NullFoodEnricher,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _needs_enrichment(item: FoodItem) -> bool:
    """A dish with no summary and no ingredient tags was never enriched."""
    return not (item.assistant_summary or item.ingredient_tags or item.main_ingredients)


class MenuService:
    def __init__(
        self,
        *,
        session: Session,
        repository: MenuRepository,
        clock: Callable[[], datetime] | None = None,
        enricher: FoodEnricher | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._clock = clock or _utcnow
        self._enricher = enricher or NullFoodEnricher()

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

    def enrich_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuEnrichResponse:
        """The second LLM pass: tag the dishes, then score the verdicts.

        Deliberately off the scan path — scanning must stay fast, and nobody needs
        taste tags until they are actually standing in front of the menu deciding
        what to order.

        Idempotent: dishes that already carry tags are skipped, so re-opening a
        menu costs nothing. Never raises at the caller: a dead enricher costs tags,
        never the menu, because the dishes, prices and allergens all came from
        extraction and are already on screen.
        """
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        total = len(menu.food_items)

        pending = [item for item in menu.food_items if _needs_enrichment(item)]
        if not pending:
            return self._enrich_response(
                menu=menu,
                user_id=user_id,
                status=EnrichmentStatus.ALREADY_ENRICHED,
                total=total,
                pending=0,
                enriched=0,
                recommendations_written=0,
            )

        dishes = [
            DishInput(
                key=str(item.id),
                name=item.translated_name or item.original_name,
                description=(
                    item.translated_description or item.original_description or ""
                ),
                category=item.category or "",
            )
            for item in pending
        ]

        try:
            enrichment = self._enricher.enrich_dishes(
                dishes,
                target_language=menu.target_language or "en",
            )
        except Exception:
            logger.warning(
                "menu_enrich_failed menu_id=%s — serving the menu untagged",
                menu_id,
                exc_info=True,
            )
            enrichment = {}

        enriched_count = 0
        for item in pending:
            update = enrichment.get(str(item.id))
            if not update:
                continue
            for field, value in update.items():
                setattr(item, field, value)
            enriched_count += 1

        recommendations_written = 0
        if enriched_count:
            self._session.flush()
            recommendations_written = self._rescore_verdicts(menu)
            self._session.commit()

        failed = len(pending) - enriched_count
        if enriched_count == 0:
            status = EnrichmentStatus.UNAVAILABLE
        elif failed:
            status = EnrichmentStatus.PARTIAL
        else:
            status = EnrichmentStatus.COMPLETED

        logger.info(
            "menu_enrich_done menu_id=%s status=%s enriched=%d/%d verdicts=%d",
            menu_id,
            status.value,
            enriched_count,
            len(pending),
            recommendations_written,
        )
        return self._enrich_response(
            menu=menu,
            user_id=user_id,
            status=status,
            total=total,
            pending=len(pending),
            enriched=enriched_count,
            recommendations_written=recommendations_written,
        )

    def _rescore_verdicts(self, menu: Menu) -> int:
        """Rewrite this menu's group verdicts now that the dishes carry tags.

        Only for a real (host-created) dining session: a personal menu is scored
        live from the diner's current profile and persists nothing.
        """
        dining_session = self._session.scalars(
            select(DiningSession).where(
                DiningSession.menu_id == menu.id,
                DiningSession.deleted_at.is_(None),
            )
        ).first()
        if dining_session is None:
            return 0

        # Guard the whole point of this rework: a verdict is scored FROM the tags,
        # so scoring a menu whose enrichment produced nothing would just re-create
        # the "100/100 recommended" advice we are here to delete.
        if not any(not _needs_enrichment(item) for item in menu.food_items):
            return 0

        return DiningSessionService(session=self._session).generate_recommendations(
            dining_session=dining_session,
            food_items=list(menu.food_items),
        )

    def _enrich_response(
        self,
        *,
        menu: Menu,
        user_id: uuid.UUID,
        status: EnrichmentStatus,
        total: int,
        pending: int,
        enriched: int,
        recommendations_written: int,
    ) -> MenuEnrichResponse:
        return MenuEnrichResponse(
            status=status,
            total_items=total,
            pending_items=pending,
            enriched_items=enriched,
            failed_items=pending - enriched,
            recommendations_written=recommendations_written,
            menu=self._menu_detail_with_recommendations(menu, user_id=user_id),
        )

    def _menu_detail_with_recommendations(
        self,
        menu: Menu,
        *,
        user_id: uuid.UUID | None,
    ) -> MenuDetailResponse:
        view = load_recommendation_view(
            self._session,
            menu_id=menu.id,
            user_id=user_id,
        )
        detail = _menu_detail_data(menu)
        detail.items = [
            MenuItemResponse.model_validate(item).model_copy(
                update={"recommendation": view.for_item(item)}
            )
            for item in sorted(menu.food_items, key=lambda item: item.sort_order)
        ]
        return detail

    def get_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuDetailResponse:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        return self._menu_detail_with_recommendations(menu, user_id=user_id)

    def get_menu_for_grounding(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Menu:
        """Ownership-checked menu load for the chat assistant.

        The chat only needs the dishes. It used to call ``get_menu``, which also
        resolved every verdict — a dining-session lookup, a recommendation query,
        a lazy walk of each recommendation's breakdowns and each breakdown's
        participant, and two Pydantic passes over every dish — and then threw all
        of it away. On a 40-dish menu that was well over a hundred queries, per
        chat message.
        """
        return self._get_owned_menu(menu_id=menu_id, user_id=user_id)

    def list_menu_items(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
        query: ListMenuItemsQuery,
    ) -> tuple[list[MenuItemResponse], int]:
        self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        offset = (query.page - 1) * query.page_size
        items = self._repository.list_items_for_menu(
            self._session,
            menu_id=menu_id,
            search=query.search,
            min_price=query.min_price,
            max_price=query.max_price,
            limit=query.page_size,
            offset=offset,
        )
        total = self._repository.count_items_for_menu(
            self._session,
            menu_id=menu_id,
            search=query.search,
            min_price=query.min_price,
            max_price=query.max_price,
        )

        view = load_recommendation_view(
            self._session,
            menu_id=menu_id,
            user_id=user_id,
        )
        items_response = [
            MenuItemResponse.model_validate(item).model_copy(
                update={"recommendation": view.for_item(item)}
            )
            for item in items
        ]
        return items_response, total

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

    def update_menu_item(
        self,
        *,
        menu_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: UpdateMenuItemRequest,
    ) -> MenuItemResponse:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        item = _find_menu_item(menu, item_id)
        now = self._clock()

        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if isinstance(value, str):
                value = value.strip() or None
            if field_name == "currency" and value:
                value = value.upper()
            setattr(item, field_name, value)

        item.updated_at = now
        menu.updated_at = now
        self._repository.save_item(self._session, item)
        self._repository.save(self._session, menu)
        self._session.commit()
        return MenuItemResponse.model_validate(item)

    def delete_menu_item(
        self,
        *,
        menu_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)
        item = _find_menu_item(menu, item_id)
        menu.food_items = [
            food_item for food_item in menu.food_items if food_item.id != item_id
        ]
        menu.updated_at = self._clock()
        self._repository.delete_item(self._session, item)
        self._repository.save(self._session, menu)
        self._session.commit()

    def _get_owned_menu(self, *, menu_id: uuid.UUID, user_id: uuid.UUID) -> Menu:
        menu = self._repository.get_by_id(self._session, menu_id=menu_id)
        if menu is None:
            raise MenuNotFoundError()
        if menu.scan_session.user_id != user_id:
            raise MenuForbiddenError()
        return menu


def _find_menu_item(menu: Menu, item_id: uuid.UUID) -> FoodItem:
    for item in menu.food_items:
        if item.id == item_id:
            return item
    raise MenuItemNotFoundError()


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
