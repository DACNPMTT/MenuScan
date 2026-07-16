"""The second LLM pass, against a real database.

These exist because the enrichment feature shipped completely broken and every
test still passed. `enrich_menu` referenced a column that does not exist
(`FoodItemRecommendationParticipantBreakdown.recommendation_id`; the real name is
`food_item_recommendation_id`), so it raised AttributeError, 500'd, and rolled
back — every single call. The LLM was paid for on every menu open and 100% of its
output was thrown away, and the frontend swallowed the error so nobody saw it.

Nothing caught it because no test ever ran `enrich_menu` against a real session.
That is the gap these close: they touch the DB, and they assert after
`expire_all()`, so "committed" means committed and not merely dirty in the
identity map.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from src.modules.dining.models import (
    DiningSession,
    DiningSessionMode,
    DiningSessionParticipant,
    DiningSessionParticipantPreference,
    DiningSessionStatus,
    FoodItemRecommendation,
    FoodItemRecommendationParticipantBreakdown,
    RecommendationVerdict,
)
from src.modules.identity.models import (
    FoodProfile,
    FoodProfilePreference,
    PreferenceType,
    User,
)
from src.modules.menu.exceptions import MenuForbiddenError
from src.modules.menu.models import FoodItem, Menu
from src.modules.menu.repository import MenuRepository
from src.modules.menu.schemas import EnrichmentStatus
from src.modules.menu.service import MenuService
from src.modules.menu_scan.food_enricher import DishInput
from src.modules.menu_scan.models import ScanSession, ScanStatus

pytestmark = pytest.mark.usefixtures("db_session")


SHRIMP = "Gỏi cuốn tôm"
PORK = "Thịt kho"


class StubEnricher:
    """Returns canned tags — or blows up, which the menu must survive."""

    def __init__(
        self,
        results: dict[str, dict[str, Any]] | None = None,
        *,
        raises: bool = False,
    ) -> None:
        self._results = results or {}
        self._raises = raises
        self.calls = 0

    def enrich_dishes(
        self,
        dishes: list[DishInput],
        *,
        target_language: str,
    ) -> dict[str, dict[str, Any]]:
        self.calls += 1
        if self._raises:
            raise RuntimeError("gemini is down")
        # Key by dish name so the seed helper doesn't need to know the item ids.
        by_name = {dish.name: dish.key for dish in dishes}
        return {
            by_name[name]: fields
            for name, fields in self._results.items()
            if name in by_name
        }


def _tags(*, seafood: bool) -> dict[str, Any]:
    return {
        "assistant_summary": "Món cuốn thanh mát." if seafood else "Món kho đậm đà.",
        "main_ingredients": ["tôm", "rau"] if seafood else ["thịt heo", "trứng"],
        "ingredient_tags": ["shrimp"] if seafood else ["pork"],
        "flavor_tags": ["fresh"] if seafood else ["savory"],
        "spice_level": 0,
        "richness_level": 1 if seafood else 4,
    }


def _seed(
    session: Session,
    *,
    with_group_session: bool = False,
    with_allergy: bool = True,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Build user (+ default profile) → scan → menu → 2 untagged dishes."""
    user = User(email=f"diner-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()

    profile = FoodProfile(
        user_id=user.id,
        display_name="Hà",
        preferred_language="vi",
        is_default=True,
    )
    if with_allergy:
        profile.preferences = [
            FoodProfilePreference(
                code="seafood",
                category="allergen",
                preference_type=PreferenceType.ALLERGY,
                importance=5,
            )
        ]
    session.add(profile)

    now = datetime.now(timezone.utc)
    scan = ScanSession(
        user_id=user.id,
        source_object_key=f"users/{user.id}/scans/{uuid.uuid4()}/source",
        source_file_name="menu.png",
        source_mime_type="image/png",
        source_file_size=1024,
        source_page_count=1,
        target_language="vi",
        status=ScanStatus.COMPLETED,
        progress=100,
        started_at=now,
        completed_at=now,
    )
    session.add(scan)
    session.flush()

    menu = Menu(
        scan_session_id=scan.id,
        title="Quán Việt",
        target_language="vi",
        default_currency="VND",
    )
    # allergens come from EXTRACTION, not enrichment — they are safety data and the
    # scan already infers them. Enrichment adds the taste profile on top.
    menu.food_items = [
        FoodItem(
            original_name=SHRIMP,
            translated_name=SHRIMP,
            allergens=["seafood", "shellfish"],
            sort_order=0,
        ),
        FoodItem(
            original_name=PORK,
            translated_name=PORK,
            dietary_tags=["contains_pork"],
            sort_order=1,
        ),
    ]
    session.add(menu)
    session.flush()

    if with_group_session:
        dining_session = DiningSession(
            created_by_user_id=user.id,
            scan_session_id=scan.id,
            menu_id=menu.id,
            mode=DiningSessionMode.GROUP,
            status=DiningSessionStatus.COMPLETED,
        )
        participant = DiningSessionParticipant(
            dining_session=dining_session,
            display_name="Bạn cùng bàn",
        )
        participant.preferences = [
            DiningSessionParticipantPreference(
                code="seafood",
                category="allergen",
                preference_type=PreferenceType.ALLERGY,
                importance=5,
            )
        ]
        dining_session.participants = [participant]
        session.add(dining_session)

    session.flush()
    return menu.id, user.id


def _service(session: Session, enricher: StubEnricher) -> MenuService:
    return MenuService(
        session=session,
        repository=MenuRepository(),
        enricher=enricher,  # type: ignore[arg-type]
    )


def _shrimp(items: list[Any]) -> Any:
    return next(item for item in items if item.original_name == SHRIMP)


# Scope every assertion to the menu under test. Querying whole tables passes in
# isolation and then fails in the full suite, because the DB-backed pipeline tests
# commit their own rows into the same schema.
def _items(session: Session, menu_id: uuid.UUID) -> list[FoodItem]:
    return session.query(FoodItem).filter(FoodItem.menu_id == menu_id).all()


def _session_of(session: Session, menu_id: uuid.UUID) -> DiningSession:
    return session.query(DiningSession).filter(DiningSession.menu_id == menu_id).one()


def _verdict_count(session: Session, menu_id: uuid.UUID) -> int:
    item_ids = [item.id for item in _items(session, menu_id)]
    if not item_ids:
        return 0
    return (
        session.query(FoodItemRecommendation)
        .filter(FoodItemRecommendation.food_item_id.in_(item_ids))
        .count()
    )


def _breakdown_count(session: Session, menu_id: uuid.UUID) -> int:
    recommendation_ids = [
        recommendation.id
        for recommendation in session.query(FoodItemRecommendation)
        .filter(
            FoodItemRecommendation.food_item_id.in_(
                [item.id for item in _items(session, menu_id)]
            )
        )
        .all()
    ]
    if not recommendation_ids:
        return 0
    return (
        session.query(FoodItemRecommendationParticipantBreakdown)
        .filter(
            FoodItemRecommendationParticipantBreakdown.food_item_recommendation_id.in_(
                recommendation_ids
            )
        )
        .count()
    )


def test_enrich_menu_persists_tags_and_verdicts(db_session: Session) -> None:
    """The regression test. This is what 500'd on every call before the fix."""
    menu_id, user_id = _seed(db_session, with_group_session=True)
    enricher = StubEnricher({SHRIMP: _tags(seafood=True), PORK: _tags(seafood=False)})

    response = _service(db_session, enricher).enrich_menu(
        menu_id=menu_id, user_id=user_id
    )

    assert response.status == EnrichmentStatus.COMPLETED
    assert response.enriched_items == 2
    assert response.failed_items == 0
    assert response.recommendations_written == 2

    # expire_all: read the rows back from the DB, not from the identity map — the
    # old code set the attributes fine and then lost them all on rollback.
    db_session.expire_all()
    items = _items(db_session, menu_id)
    assert all(item.assistant_summary for item in items)
    assert _shrimp(items).ingredient_tags == ["shrimp"]

    assert _verdict_count(db_session, menu_id) == 2
    assert _breakdown_count(db_session, menu_id) == 2


def test_enrich_menu_scores_the_allergy_it_just_learned_about(
    db_session: Session,
) -> None:
    """The whole point: a verdict is only worth anything once the tags exist.

    Seed the exact garbage the old code produced — shrimp marked 100/RECOMMENDED,
    scored when the dish had no tags — and check enrichment replaces it with AVOID
    for a diner who is allergic to seafood.
    """
    menu_id, user_id = _seed(db_session, with_group_session=True)
    shrimp_item = _shrimp(_items(db_session, menu_id))
    dining_session = _session_of(db_session, menu_id)
    db_session.add(
        FoodItemRecommendation(
            dining_session_id=dining_session.id,
            food_item_id=shrimp_item.id,
            verdict=RecommendationVerdict.RECOMMENDED,
            score=100,
        )
    )
    db_session.flush()

    enricher = StubEnricher({SHRIMP: _tags(seafood=True), PORK: _tags(seafood=False)})
    response = _service(db_session, enricher).enrich_menu(
        menu_id=menu_id, user_id=user_id
    )

    verdict = _shrimp(response.menu.items).recommendation
    assert verdict is not None
    assert verdict.verdict == "AVOID"

    # Delete-then-insert, so the stale row is gone rather than duplicated — and no
    # IntegrityError on the (session, dish) unique key.
    db_session.expire_all()
    assert _verdict_count(db_session, menu_id) == 2


def test_enrich_menu_is_idempotent(db_session: Session) -> None:
    menu_id, user_id = _seed(db_session, with_group_session=True)
    enricher = StubEnricher({SHRIMP: _tags(seafood=True), PORK: _tags(seafood=False)})
    service = _service(db_session, enricher)

    service.enrich_menu(menu_id=menu_id, user_id=user_id)
    second = service.enrich_menu(menu_id=menu_id, user_id=user_id)

    assert second.status == EnrichmentStatus.ALREADY_ENRICHED
    assert enricher.calls == 1  # re-opening the menu costs no LLM call
    db_session.expire_all()
    assert _verdict_count(db_session, menu_id) == 2


def test_enrich_menu_reports_a_partial_pass(db_session: Session) -> None:
    menu_id, user_id = _seed(db_session, with_group_session=True)
    enricher = StubEnricher({SHRIMP: _tags(seafood=True)})  # pork batch came back empty

    response = _service(db_session, enricher).enrich_menu(
        menu_id=menu_id, user_id=user_id
    )

    assert response.status == EnrichmentStatus.PARTIAL
    assert response.enriched_items == 1
    assert response.failed_items == 1
    assert len(response.menu.items) == 2  # the untagged dish is still on the menu


def test_enrich_menu_survives_a_dead_enricher(db_session: Session) -> None:
    """Tags are a bonus. The menu is not."""
    menu_id, user_id = _seed(db_session, with_group_session=True)

    response = _service(db_session, StubEnricher(raises=True)).enrich_menu(
        menu_id=menu_id, user_id=user_id
    )

    assert response.status == EnrichmentStatus.UNAVAILABLE
    assert response.enriched_items == 0
    assert len(response.menu.items) == 2

    # Crucially: no verdicts written. Scoring untagged dishes is the bug, not a
    # graceful degradation of it.
    db_session.expire_all()
    assert _verdict_count(db_session, menu_id) == 0


def test_personal_menu_is_scored_live_and_persists_no_rows(
    db_session: Session,
) -> None:
    """An ordinary scan has no dining session — one reader, nothing to store."""
    menu_id, user_id = _seed(db_session, with_group_session=False)
    enricher = StubEnricher({SHRIMP: _tags(seafood=True), PORK: _tags(seafood=False)})

    response = _service(db_session, enricher).enrich_menu(
        menu_id=menu_id, user_id=user_id
    )

    assert response.status == EnrichmentStatus.COMPLETED
    assert response.recommendations_written == 0

    verdict = _shrimp(response.menu.items).recommendation
    assert verdict is not None
    assert verdict.verdict == "AVOID"  # scored live from the current food profile

    db_session.expire_all()
    assert _verdict_count(db_session, menu_id) == 0


def test_a_diner_who_declared_nothing_gets_no_verdict(db_session: Session) -> None:
    """No signal, no advice.

    The scorer starts every dish at 100/RECOMMENDED and only subtracts when a
    preference matches, so a diner who has told us nothing used to be told every
    single dish was a 100/100 recommendation. Confident, and about nothing.
    """
    menu_id, user_id = _seed(db_session, with_group_session=False, with_allergy=False)
    enricher = StubEnricher({SHRIMP: _tags(seafood=True), PORK: _tags(seafood=False)})

    response = _service(db_session, enricher).enrich_menu(
        menu_id=menu_id, user_id=user_id
    )

    assert response.status == EnrichmentStatus.COMPLETED
    assert all(item.recommendation is None for item in response.menu.items)


def test_enrich_menu_rejects_a_non_owner(db_session: Session) -> None:
    menu_id, _ = _seed(db_session)
    stranger = User(email=f"stranger-{uuid.uuid4().hex[:8]}@example.com")
    db_session.add(stranger)
    db_session.flush()

    with pytest.raises(MenuForbiddenError):
        _service(db_session, StubEnricher()).enrich_menu(
            menu_id=menu_id, user_id=stranger.id
        )
