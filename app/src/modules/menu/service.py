from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.modules.menu.exceptions import (
    MenuForbiddenError,
    MenuItemNotFoundError,
    MenuNotFoundError,
)
from src.modules.menu.models import FoodItem, Menu, MenuStatus
from src.modules.menu.repository import MenuRepository
from src.modules.menu.schemas import (
    CreateMenuItemRequest,
    ListMenuItemsQuery,
    MenuDetailResponse,
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
from src.modules.menu_scan.schemas import (
    ParticipantBreakdownResponse,
    RecommendationResponse,
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
    ) -> MenuDetailResponse:
        """Fill in food intelligence for dishes that lack it, then rescore verdicts.

        This is the second LLM pass, deliberately off the scan path: scanning must
        stay fast, and tags are only needed once the diner is actually looking at
        the menu. Idempotent — dishes already enriched are skipped, so the diner
        pays for this once and re-opening the menu is free.
        """
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)

        pending = [item for item in menu.food_items if _needs_enrichment(item)]
        if not pending:
            return self.get_menu(menu_id=menu_id, user_id=user_id)

        dishes = [
            DishInput(
                key=str(item.id),
                name=item.translated_name or item.original_name,
                description=item.translated_description
                or item.original_description
                or "",
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
            # Never fail the menu screen over tags. The dishes, prices and
            # allergens all came from extraction and are already on screen.
            logger.warning(
                "menu_enrich_failed menu_id=%s — serving the menu untagged",
                menu_id,
                exc_info=True,
            )
            return self.get_menu(menu_id=menu_id, user_id=user_id)

        enriched_count = 0
        for item in pending:
            update = enrichment.get(str(item.id))
            if not update:
                continue
            for field, value in update.items():
                setattr(item, field, value)
            enriched_count += 1

        if enriched_count:
            self._session.flush()
            # Verdicts are scored from the food-intelligence fields, so the rows
            # written at scan time were scored against empty tags. Redo them now
            # that the tags exist, or the menu would show stale advice forever.
            self._regenerate_recommendations(menu)
            self._session.commit()

        logger.info(
            "menu_enrich_complete menu_id=%s enriched=%d pending=%d",
            menu_id,
            enriched_count,
            len(pending),
        )
        return self.get_menu(menu_id=menu_id, user_id=user_id)

    def _regenerate_recommendations(self, menu: Menu) -> None:
        from src.modules.dining.models import (
            DiningSession,
            FoodItemRecommendation,
            FoodItemRecommendationParticipantBreakdown,
        )
        from src.modules.dining.service import DiningSessionService

        if not hasattr(self._session, "query"):
            return

        dining_session = (
            self._session.query(DiningSession)
            .filter(DiningSession.menu_id == menu.id)
            .first()
        )
        if dining_session is None:
            return

        stale = (
            self._session.query(FoodItemRecommendation)
            .filter(FoodItemRecommendation.dining_session_id == dining_session.id)
            .all()
        )
        for recommendation in stale:
            self._session.query(
                FoodItemRecommendationParticipantBreakdown
            ).filter(
                FoodItemRecommendationParticipantBreakdown.recommendation_id
                == recommendation.id
            ).delete(synchronize_session=False)
            self._session.delete(recommendation)
        self._session.flush()

        DiningSessionService(session=self._session).generate_recommendations(
            dining_session=dining_session,
            menu=menu,
            food_items=list(menu.food_items),
            draft_items=None,
        )

    def get_menu(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MenuDetailResponse:
        menu = self._get_owned_menu(menu_id=menu_id, user_id=user_id)

        from src.modules.dining.models import DiningSession, FoodItemRecommendation
        from src.modules.dining.service import DiningSessionService
        from src.modules.identity.models import FoodProfile

        dining_session = None
        if hasattr(self._session, "query"):
            dining_session = (
                self._session.query(DiningSession)
                .filter(DiningSession.menu_id == menu_id)
                .first()
            )

        rec_by_food_id = {}
        default_profile = None

        if dining_session is not None:
            recs = (
                self._session.query(FoodItemRecommendation)
                .filter(FoodItemRecommendation.dining_session_id == dining_session.id)
                .all()
            )
            rec_by_food_id = {r.food_item_id: r for r in recs}
        else:
            if hasattr(self._session, "query"):
                default_profile = (
                    self._session.query(FoodProfile)
                    .filter(
                        FoodProfile.user_id == user_id,
                        FoodProfile.is_default,
                        FoodProfile.deleted_at.is_(None),
                    )
                    .first()
                )

        items_response = []
        for item in sorted(menu.food_items, key=lambda item: item.sort_order):
            rec_data = None
            if dining_session is not None:
                r = rec_by_food_id.get(item.id)
                if r is not None:
                    rec_data = _recommendation_response(r)
            elif default_profile is not None:
                verdict, score, fit, risk = DiningSessionService._score_item_for_diner(
                    item, default_profile.preferences
                )
                display_name = default_profile.display_name or "Bạn"
                rec_data = _personal_recommendation_response(
                    display_name=display_name,
                    verdict=verdict.value,
                    score=score,
                    fit=fit,
                    risk=risk,
                )

            items_response.append(
                MenuItemResponse.model_validate(item).model_copy(
                    update={"recommendation": rec_data}
                )
            )

        detail = _menu_detail_data(menu)
        detail.items = items_response
        return detail

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

        from src.modules.dining.models import DiningSession, FoodItemRecommendation
        from src.modules.dining.service import DiningSessionService
        from src.modules.identity.models import FoodProfile

        dining_session = None
        if hasattr(self._session, "query"):
            dining_session = (
                self._session.query(DiningSession)
                .filter(DiningSession.menu_id == menu_id)
                .first()
            )

        rec_by_food_id = {}
        default_profile = None

        if dining_session is not None:
            recs = (
                self._session.query(FoodItemRecommendation)
                .filter(FoodItemRecommendation.dining_session_id == dining_session.id)
                .all()
            )
            rec_by_food_id = {r.food_item_id: r for r in recs}
        else:
            if hasattr(self._session, "query"):
                default_profile = (
                    self._session.query(FoodProfile)
                    .filter(
                        FoodProfile.user_id == user_id,
                        FoodProfile.is_default,
                        FoodProfile.deleted_at.is_(None),
                    )
                    .first()
                )

        items_response = []
        for item in items:
            rec_data = None
            if dining_session is not None:
                r = rec_by_food_id.get(item.id)
                if r is not None:
                    rec_data = _recommendation_response(r)
            elif default_profile is not None:
                verdict, score, fit, risk = DiningSessionService._score_item_for_diner(
                    item, default_profile.preferences
                )
                display_name = default_profile.display_name or "Bạn"
                rec_data = _personal_recommendation_response(
                    display_name=display_name,
                    verdict=verdict.value,
                    score=score,
                    fit=fit,
                    risk=risk,
                )

            items_response.append(
                MenuItemResponse.model_validate(item).model_copy(
                    update={"recommendation": rec_data}
                )
            )

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


def _recommendation_response(recommendation: object) -> RecommendationResponse:
    breakdowns = [
        ParticipantBreakdownResponse(
            display_name=getattr(breakdown.participant, "display_name", "Thành viên"),
            verdict=breakdown.verdict.value,
            score=float(breakdown.score) if breakdown.score is not None else None,
            explanation=breakdown.explanation,
            fit_reasons=breakdown.fit_reasons or [],
            risk_reasons=breakdown.risk_reasons or [],
        )
        for breakdown in getattr(recommendation, "participant_breakdowns", []) or []
    ]
    return RecommendationResponse(
        verdict=recommendation.verdict.value,
        score=float(recommendation.score) if recommendation.score is not None else None,
        explanation=recommendation.explanation,
        why_suitable=recommendation.why_suitable,
        why_not_suitable=recommendation.why_not_suitable,
        suggested_for=recommendation.suggested_for or [],
        warning_for=recommendation.warning_for or [],
        fit_reasons=recommendation.fit_reasons or [],
        risk_reasons=recommendation.risk_reasons or [],
        warning_reasons=recommendation.warning_reasons or [],
        participant_breakdowns=breakdowns,
    )


def _personal_recommendation_response(
    *,
    display_name: str,
    verdict: str,
    score: float,
    fit: list[str],
    risk: list[str],
) -> RecommendationResponse:
    return RecommendationResponse(
        verdict=verdict,
        score=score,
        explanation=f"Độ phù hợp cá nhân {score:.0f}/100.",
        why_suitable=", ".join(fit) if fit else None,
        why_not_suitable=", ".join(risk) if risk else None,
        suggested_for=[display_name] if verdict == "RECOMMENDED" else [],
        warning_for=[display_name] if verdict == "AVOID" else [],
        fit_reasons=fit,
        risk_reasons=risk,
        warning_reasons=risk if verdict in {"AVOID", "CAUTION"} else [],
        participant_breakdowns=[
            ParticipantBreakdownResponse(
                display_name=display_name,
                verdict=verdict,
                score=score,
                explanation=f"Độ phù hợp cá nhân {score:.0f}/100.",
                fit_reasons=fit,
                risk_reasons=risk,
            )
        ],
    )


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
