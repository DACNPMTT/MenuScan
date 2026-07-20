"""Application service for the rule-based feed.

Owns the transaction boundary. Pulls the user's preferences from
``food_profile_preferences`` (likes/avoids/allergens), scores every cached
restaurant, filters by radius + saved + seen, applies a diversity penalty
left-to-right, and returns the ranked cards.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.feed_recommend.data_loader import (
    RestaurantData,
    get_restaurant_by_source_id,
    load_restaurants,
)
from src.modules.feed_recommend.exceptions import (
    AlreadySavedError,
    LocationNotSetError,
    RestaurantNotFoundError,
)
from src.modules.feed_recommend.repository import (
    UserLocationRepository,
    UserRestaurantSaveRepository,
    UserRestaurantSeenRepository,
)
from src.modules.feed_recommend.schemas import (
    FeedResponse,
    LocationResponse,
    MarkSeenRequest,
    RestaurantCardResponse,
    ScoreBreakdown as SchemaScoreBreakdown,
    SetLocationRequest,
    meal_briefs_from_raw,
)
from src.modules.feed_recommend.scoring import (
    RecentTypeWindow,
    ScoreBreakdown,
    diversity_penalty,
    haversine_km,
    score_restaurant,
)
from src.modules.identity.models import (
    FoodProfile,
    FoodProfilePreference,
    PreferenceType,
    User,
)


def _user_preference_sets(
    session: Session,
    user_id: uuid.UUID,
) -> tuple[set[str], set[str], set[str]]:
    """Bucket the user's default profile preferences into likes/avoids/allergens.

    Returns three empty sets if the user has no default profile yet — the
    scorer then disables the taste term and falls back to distance+star+price.
    """
    profile = session.scalars(
        select(FoodProfile)
        .where(
            FoodProfile.user_id == user_id,
            FoodProfile.deleted_at.is_(None),
            FoodProfile.is_default.is_(True),
        )
        .limit(1)
    ).first()
    if profile is None:
        return set(), set(), set()
    preferences = list(
        session.scalars(
            select(FoodProfilePreference).where(
                FoodProfilePreference.food_profile_id == profile.id
            )
        )
    )
    likes: set[str] = set()
    avoids: set[str] = set()
    allergens: set[str] = set()
    for pref in preferences:
        code = pref.code.strip().lower()
        if not code:
            continue
        if pref.preference_type == PreferenceType.LIKE:
            likes.add(code)
        elif pref.preference_type in (PreferenceType.AVOID, PreferenceType.DISLIKE):
            avoids.add(code)
        elif pref.preference_type == PreferenceType.ALLERGY:
            allergens.add(code)
    return likes, avoids, allergens


def _build_card(
    restaurant: RestaurantData,
    breakdown: ScoreBreakdown,
    match_reasons: list[str],
    caution_reasons: list[str],
    *,
    distance_km: float | None,
    saved: bool,
    seen_action: str | None,
) -> RestaurantCardResponse:
    return RestaurantCardResponse(
        source_id=restaurant.source_id,
        name=restaurant.name,
        address=restaurant.address,
        lat=restaurant.lat,
        lng=restaurant.lng,
        avg_price=restaurant.avg_price,
        star=restaurant.star,
        image_url=restaurant.image_url,
        phone_num=restaurant.phone_num,
        type=list(restaurant.type),
        meals=meal_briefs_from_raw(restaurant.meals),
        semantic_text=restaurant.semantic_text,
        distance_km=distance_km,
        score=breakdown.total,
        score_breakdown=SchemaScoreBreakdown(
            distance=breakdown.distance,
            quality=breakdown.quality,
            price_fit=breakdown.price_fit,
            taste_match=breakdown.taste_match,
            allergy_penalty=breakdown.allergy_penalty,
            total=breakdown.total,
        ),
        match_reasons=match_reasons,
        caution_reasons=caution_reasons,
        saved=saved,
        seen_action=seen_action,
    )


class FeedRecommendService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._locations = UserLocationRepository()
        self._saves = UserRestaurantSaveRepository()
        self._seen = UserRestaurantSeenRepository()

    # --- Feed ---------------------------------------------------------------

    def get_feed(
        self,
        user: User,
        *,
        radius_km: float = 5.0,
        limit: int = 20,
    ) -> FeedResponse:
        location = self._locations.get(self._session, user.id)
        if location is None:
            raise LocationNotSetError()

        likes, avoids, allergens = _user_preference_sets(self._session, user.id)
        saved_ids = self._saves.source_ids(self._session, user.id)
        seen_ids = self._seen.source_ids(self._session, user.id)

        restaurants = load_restaurants()
        scored: list[tuple[float, RestaurantData, ScoreBreakdown, list[str], list[str], float]] = []
        for restaurant in restaurants:
            if restaurant.source_id in seen_ids or restaurant.source_id in saved_ids:
                continue
            breakdown, match_reasons, caution_reasons = score_restaurant(
                restaurant,
                user_lat=location.lat,
                user_lng=location.lng,
                user_likes=likes,
                user_avoids=avoids,
                user_allergens=allergens,
                user_price_band=user.price_band_cents,
            )
            distance_km = haversine_km(location.lat, location.lng, restaurant.lat, restaurant.lng)
            if distance_km > radius_km:
                continue
            scored.append(
                (
                    breakdown.total,
                    restaurant,
                    breakdown,
                    match_reasons,
                    caution_reasons,
                    distance_km,
                )
            )

        # Greedy: walk the base-score desc order; for each restaurant compute
        # the diversity penalty from what we've *kept* in the last 3 cards,
        # subtract it from the displayed score (does NOT change take order),
        # then push its cuisines into the rolling window.
        scored.sort(key=lambda row: row[0], reverse=True)
        window = RecentTypeWindow()
        items: list[RestaurantCardResponse] = []
        for _base, restaurant, breakdown, match_reasons, caution_reasons, distance_km in scored:
            penalty = diversity_penalty(window.flat(), list(restaurant.type))
            adjusted_total = max(0.0, breakdown.total - penalty)
            adjusted = ScoreBreakdown(
                distance=breakdown.distance,
                quality=breakdown.quality,
                price_fit=breakdown.price_fit,
                taste_match=breakdown.taste_match,
                allergy_penalty=breakdown.allergy_penalty,
                total=adjusted_total,
            )
            window.push(list(restaurant.type))
            items.append(
                _build_card(
                    restaurant,
                    adjusted,
                    match_reasons,
                    caution_reasons,
                    distance_km=distance_km,
                    saved=False,
                    seen_action=None,
                )
            )
            if len(items) >= limit:
                break

        return FeedResponse(
            items=items,
            total_available=len(scored),
            location_source=location.source,
            radius_km=radius_km,
        )

    # --- Save / seen --------------------------------------------------------

    def mark_seen(
        self,
        user: User,
        restaurant_source_id: int,
        payload: MarkSeenRequest,
    ) -> None:
        if get_restaurant_by_source_id(restaurant_source_id) is None:
            raise RestaurantNotFoundError(source_id=restaurant_source_id)
        self._seen.mark(
            self._session,
            user_id=user.id,
            restaurant_source_id=restaurant_source_id,
            action=payload.action,
        )
        self._session.commit()

    def save_restaurant(
        self,
        user: User,
        restaurant_source_id: int,
    ) -> RestaurantCardResponse:
        restaurant = get_restaurant_by_source_id(restaurant_source_id)
        if restaurant is None:
            raise RestaurantNotFoundError(source_id=restaurant_source_id)
        try:
            self._saves.add(
                self._session,
                user_id=user.id,
                restaurant_source_id=restaurant_source_id,
            )
        except Exception as exc:
            # UNIQUE violation ⇒ already saved. Roll back so the session is
            # reusable for the read below.
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                self._session.rollback()
                raise AlreadySavedError() from exc
            raise
        # Implicit: a saved restaurant leaves the feed, so mark it seen too.
        self._seen.mark(
            self._session,
            user_id=user.id,
            restaurant_source_id=restaurant_source_id,
            action="view",
        )
        self._session.commit()
        return self._detail_card(user, restaurant, saved=True)

    def unsave_restaurant(
        self,
        user: User,
        restaurant_source_id: int,
    ) -> None:
        self._saves.remove(
            self._session,
            user_id=user.id,
            restaurant_source_id=restaurant_source_id,
        )
        self._session.commit()

    def list_saved(self, user: User) -> list[RestaurantCardResponse]:
        saves = self._saves.list(self._session, user.id)
        location = self._locations.get(self._session, user.id)
        likes, avoids, allergens = _user_preference_sets(self._session, user.id)
        cards: list[RestaurantCardResponse] = []
        for save in saves:
            restaurant = get_restaurant_by_source_id(save.restaurant_source_id)
            if restaurant is None:
                continue  # orphan: restaurant dropped from JSON; UI shows stale
            breakdown, match_reasons, caution_reasons = score_restaurant(
                restaurant,
                user_lat=location.lat if location else restaurant.lat,
                user_lng=location.lng if location else restaurant.lng,
                user_likes=likes,
                user_avoids=avoids,
                user_allergens=allergens,
                user_price_band=user.price_band_cents,
            )
            distance_km = (
                haversine_km(location.lat, location.lng, restaurant.lat, restaurant.lng)
                if location is not None
                else None
            )
            cards.append(
                _build_card(
                    restaurant,
                    breakdown,
                    match_reasons,
                    caution_reasons,
                    distance_km=distance_km,
                    saved=True,
                    seen_action="view",
                )
            )
        return cards

    def get_restaurant_detail(
        self,
        user: User,
        restaurant_source_id: int,
    ) -> RestaurantCardResponse:
        restaurant = get_restaurant_by_source_id(restaurant_source_id)
        if restaurant is None:
            raise RestaurantNotFoundError(source_id=restaurant_source_id)
        saved_ids = self._saves.source_ids(self._session, user.id)
        return self._detail_card(
            user,
            restaurant,
            saved=restaurant.source_id in saved_ids,
        )

    def _detail_card(
        self,
        user: User,
        restaurant: RestaurantData,
        *,
        saved: bool,
    ) -> RestaurantCardResponse:
        location = self._locations.get(self._session, user.id)
        likes, avoids, allergens = _user_preference_sets(self._session, user.id)
        breakdown, match_reasons, caution_reasons = score_restaurant(
            restaurant,
            user_lat=location.lat if location else restaurant.lat,
            user_lng=location.lng if location else restaurant.lng,
            user_likes=likes,
            user_avoids=avoids,
            user_allergens=allergens,
            user_price_band=user.price_band_cents,
        )
        distance_km = (
            haversine_km(location.lat, location.lng, restaurant.lat, restaurant.lng)
            if location is not None
            else None
        )
        return _build_card(
            restaurant,
            breakdown,
            match_reasons,
            caution_reasons,
            distance_km=distance_km,
            saved=saved,
            seen_action=None,
        )

    # --- Location -----------------------------------------------------------

    def get_location(self, user: User) -> LocationResponse | None:
        location = self._locations.get(self._session, user.id)
        if location is None:
            return None
        return LocationResponse.model_validate(location)

    def set_location(
        self,
        user: User,
        payload: SetLocationRequest,
    ) -> LocationResponse:
        location = self._locations.upsert(
            self._session,
            user_id=user.id,
            lat=payload.lat,
            lng=payload.lng,
            address_text=payload.address_text,
            source=payload.source,
        )
        self._session.commit()
        # Refresh to pick up the server-set ``updated_at`` default.
        self._session.refresh(location)
        return LocationResponse.model_validate(location)



__all__ = [
    "FeedRecommendService",
]
