"""Pure scoring functions for the rule-based feed.

No DB access — given a ``RestaurantData`` and the user's preference sets,
return a ``ScoreBreakdown`` plus human-readable match/caution reasons. The
service is responsible for fetching user preferences and ordering results.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from src.modules.feed_recommend.data_loader import RestaurantData

EARTH_RADIUS_KM = 6371.0

# Distance decay half-life: ``exp(-km / LAMBDA_KM)``. At 3 km a restaurant
# retains ~37% of the score it would have at 0 km; tune to taste.
DISTANCE_LAMBDA_KM = 3.0

# Allergy penalty: subtracted from the 0..100 weighted sum when the user's
# allergen matches a restaurant cuisine keyword directly. Demote, don't
# exclude — the diner may still want to know about it.
ALLERGY_PENALTY = 30.0

# Diversity: penalise the 4th-in-a-row of the same cuisine to keep the feed
# varied. ``5`` per overlapping type in the last ``WINDOW`` cards.
DIVERSITY_PENALTY_PER_HIT = 5.0
DIVERSITY_WINDOW = 3

# Base weights when every signal is present. Disabled signals redistribute
# their weight to the distance term (so closer still wins as a fallback).
WEIGHT_DISTANCE_FULL = 0.40
WEIGHT_QUALITY = 0.20
WEIGHT_PRICE_FIT = 0.15
WEIGHT_TASTE_MATCH = 0.25

# Map cuisine strings (lowercase, from the dataset's ``type[]``) to
# ``food_profile_preferences.code`` values. Covers both English canonical
# names and the Vietnamese taxonomy the production dataset ships with
# ("Quán Việt", "Quán Nhật", "Quán Thái", etc.). Unknown cuisines just
# score 0 on taste match rather than blocking the restaurant.
CUISINE_TO_PREFERENCE_CODES: dict[str, list[str]] = {
    # English canonical
    "vietnamese": ["fish_sauce", "rice", "noodles", "fresh"],
    "seafood": ["seafood"],
    "korean": ["spicy", "grilled", "soup"],
    "japanese": ["soup", "seafood"],
    "chinese": ["noodles", "rice"],
    "italian": ["heavy_cream", "deep_fried"],
    "bbq": ["grilled", "beef", "pork"],
    "vegetarian": ["vegetables"],
    "thai": ["spicy"],
    "indian": ["spicy", "vegetables"],
    # Vietnamese taxonomy (production dataset)
    "quán việt": ["fish_sauce", "rice", "noodles", "fresh"],
    "quán vi": ["fish_sauce", "rice", "noodles", "fresh"],
    "quán nhật": ["soup", "seafood"],
    "quán hàn": ["spicy", "grilled", "soup"],
    "quán thái": ["spicy"],
    "quán âu": ["heavy_cream", "deep_fried"],
    "quán ấn": ["spicy", "vegetables"],
    "quán chay": ["vegetables"],
    "đồ chay": ["vegetables"],
    "đồ ăn nhanh": ["deep_fried"],
    "thức ăn nhanh": ["deep_fried"],
    "tiệm bánh": ["sweet"],
    "quán nước": [],
    "quán cà phê": [],
}

# Direct substring match between ``restaurant.type[]`` and the user's
# allergen code. Includes Vietnamese cuisine names that are commonly
# associated with an allergen (e.g. Thai restaurants use peanut heavily).
# Indirect inference is otherwise kept conservative to avoid false-positive
# penalties.
ALLERGEN_CODE_TO_TYPE_KEYWORDS: dict[str, list[str]] = {
    "shellfish": ["shellfish", "crab", "shrimp", "lobster", "hải sản", "cua", "tôm", "ghẹ"],
    "fish": ["fish", "seafood", "hải sản", "cá"],
    "peanut": ["peanut", "quán thái", "thai", "quán ấn", "indian"],
    "seafood": ["seafood", "hải sản"],
}


@dataclass(frozen=True)
class ScoreBreakdown:
    distance: float
    quality: float
    price_fit: float | None
    taste_match: float | None
    allergy_penalty: float
    total: float


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def _weights(*, price_fit_active: bool, taste_match_active: bool) -> tuple[float, float, float, float]:
    """Return (distance, quality, price_fit, taste_match) weights, summing to 1.

    Disabled signals hand their weight to the distance term so closer-still-wins
    stays true when we know nothing else about the diner.
    """
    w_distance = WEIGHT_DISTANCE_FULL
    w_price = WEIGHT_PRICE_FIT
    w_taste = WEIGHT_TASTE_MATCH
    if not price_fit_active:
        w_distance += w_price
        w_price = 0.0
    if not taste_match_active:
        w_distance += w_taste
        w_taste = 0.0
    return w_distance, WEIGHT_QUALITY, w_price, w_taste


def _taste_overlap(
    restaurant: RestaurantData,
    user_likes: set[str],
    user_avoids: set[str],
) -> tuple[set[str], set[str]]:
    """Return (liked codes the restaurant cuisine triggers, avoided codes it triggers)."""
    restaurant_codes: set[str] = set()
    for cuisine in restaurant.type:
        restaurant_codes.update(CUISINE_TO_PREFERENCE_CODES.get(cuisine, []))
    likes_hit = restaurant_codes & user_likes
    avoids_hit = restaurant_codes & user_avoids
    return likes_hit, avoids_hit


def _allergy_match(restaurant: RestaurantData, user_allergens: set[str]) -> set[str]:
    """Return the subset of user allergens that hit any restaurant cuisine keyword."""
    if not user_allergens:
        return set()
    hits: set[str] = set()
    for allergen in user_allergens:
        triggers = ALLERGEN_CODE_TO_TYPE_KEYWORDS.get(allergen, [])
        if not triggers:
            continue
        for cuisine in restaurant.type:
            for trigger in triggers:
                if trigger in cuisine:
                    hits.add(allergen)
                    break
            if allergen in hits:
                break
    return hits


def score_restaurant(
    restaurant: RestaurantData,
    *,
    user_lat: float,
    user_lng: float,
    user_likes: set[str],
    user_avoids: set[str],
    user_allergens: set[str],
    user_price_band: int | None,
) -> tuple[ScoreBreakdown, list[str], list[str]]:
    """Score one restaurant. Returns (breakdown, match_reasons, caution_reasons).

    ``match_reasons`` and ``caution_reasons`` are short human strings the UI
    renders as chips ("Cay", "Dị ứng hải sản", etc.).
    """
    distance_km = haversine_km(user_lat, user_lng, restaurant.lat, restaurant.lng)
    distance_decay = math.exp(-distance_km / DISTANCE_LAMBDA_KM)
    quality = (restaurant.star or 0.0) / 5.0

    price_fit: float | None = None
    if user_price_band is not None and restaurant.avg_price is not None and user_price_band > 0:
        sigma = 0.5 * user_price_band + 50000
        price_fit = math.exp(-(((restaurant.avg_price - user_price_band) / sigma) ** 2))

    taste_match: float | None = None
    match_reasons: list[str] = []
    if user_likes or user_avoids:
        likes_hit, avoids_hit = _taste_overlap(restaurant, user_likes, user_avoids)
        taste_match = max(
            0.0,
            min(1.0, min(len(likes_hit), 3) / 3 - 0.5 * len(avoids_hit)),
        )
        match_reasons = sorted(likes_hit)

    caution_reasons: list[str] = []
    allergy_hits = _allergy_match(restaurant, user_allergens)
    allergy_penalty = ALLERGY_PENALTY if allergy_hits else 0.0
    caution_reasons = sorted(allergy_hits)

    w_distance, w_quality, w_price, w_taste = _weights(
        price_fit_active=price_fit is not None,
        taste_match_active=taste_match is not None,
    )

    weighted_sum = (
        w_distance * distance_decay
        + w_quality * quality
        + (w_price * price_fit if price_fit is not None else 0.0)
        + (w_taste * taste_match if taste_match is not None else 0.0)
    )
    total = max(0.0, 100.0 * weighted_sum - allergy_penalty)

    breakdown = ScoreBreakdown(
        distance=distance_decay,
        quality=quality,
        price_fit=price_fit,
        taste_match=taste_match,
        allergy_penalty=allergy_penalty,
        total=total,
    )
    return breakdown, match_reasons, caution_reasons


def diversity_penalty(recent_types: list[str], restaurant_types: list[str]) -> float:
    """Penalty for stacking the same cuisine many times in a row.

    ``recent_types`` is the flat list of cuisine strings from the previous
    ``DIVERSITY_WINDOW`` cards (caller is responsible for trimming). Returns
    ``DIVERSITY_PENALTY_PER_HIT`` times how many of this restaurant's types
    appear in that recent window.
    """
    if not recent_types or not restaurant_types:
        return 0.0
    recent_set = set(recent_types)
    overlaps = sum(1 for t in restaurant_types if t in recent_set)
    return DIVERSITY_PENALTY_PER_HIT * overlaps


class RecentTypeWindow:
    """Fixed-size rolling window of the last N cards' cuisine strings.

    Walked into ``diversity_penalty`` as the feed is built left-to-right.
    """

    def __init__(self, size: int = DIVERSITY_WINDOW) -> None:
        self._deque: deque[list[str]] = deque(maxlen=size)

    def push(self, types: list[str]) -> None:
        self._deque.append(types)

    def flat(self) -> list[str]:
        out: list[str] = []
        for types in self._deque:
            out.extend(types)
        return out
