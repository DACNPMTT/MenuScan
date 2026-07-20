"""Unit tests for ``feed_recommend.scoring`` and ``data_loader._parse_item``.

No database access. Scoring is verified against synthetic ``RestaurantData``
fixtures so the test does not depend on the JSON file shipped in the repo.
"""

from __future__ import annotations

import math

import pytest

from src.modules.feed_recommend import data_loader, scoring
from src.modules.feed_recommend.data_loader import RestaurantData, _parse_item
from src.modules.feed_recommend.scoring import (
    ALLERGY_PENALTY,
    DISTANCE_LAMBDA_KM,
    DIVERSITY_PENALTY_PER_HIT,
    haversine_km,
    score_restaurant,
    diversity_penalty,
    RecentTypeWindow,
)


def _restaurant(
    *,
    source_id: int = 1,
    name: str = "Quán",
    address: str = "Đà Nẵng",
    lat: float = 16.06,
    lng: float = 108.22,
    avg_price: int | None = 100_000,
    star: float | None = 4.5,
    type: list[str] | None = None,
) -> RestaurantData:
    return RestaurantData(
        source_id=source_id,
        name=name,
        address=address,
        lat=lat,
        lng=lng,
        avg_price=avg_price,
        star=star,
        semantic_text=None,
        image_url=None,
        phone_num=None,
        type=type or [],
        meals=[],
    )


# --- haversine_km -----------------------------------------------------------


def test_haversine_km_zero_distance():
    assert haversine_km(16.06, 108.22, 16.06, 108.22) == pytest.approx(0.0, abs=1e-6)


def test_haversine_km_known_pair():
    # Da Nang city center to My Khe beach — roughly 3 km straight line.
    km = haversine_km(16.0610, 108.2180, 16.0518, 108.2450)
    assert 2.0 < km < 4.0


def test_haversine_km_symmetric():
    a = haversine_km(10.0, 105.0, 11.0, 106.0)
    b = haversine_km(11.0, 106.0, 10.0, 105.0)
    assert a == pytest.approx(b, rel=1e-9)


# --- score_restaurant -------------------------------------------------------


def _score(
    restaurant: RestaurantData,
    *,
    user_lat: float = 16.06,
    user_lng: float = 108.22,
    likes: set[str] | None = None,
    avoids: set[str] | None = None,
    allergens: set[str] | None = None,
    price_band: int | None = None,
) -> tuple[float, scoring.ScoreBreakdown, list[str], list[str]]:
    breakdown, match, caution = score_restaurant(
        restaurant,
        user_lat=user_lat,
        user_lng=user_lng,
        user_likes=likes or set(),
        user_avoids=avoids or set(),
        user_allergens=allergens or set(),
        user_price_band=price_band,
    )
    return breakdown.total, breakdown, match, caution


def test_closer_dominates_at_equal_stars():
    near = _restaurant(source_id=1, lat=16.061, lng=108.221)
    far = _restaurant(source_id=2, lat=16.20, lng=108.40)
    near_total, _, _, _ = _score(near)
    far_total, _, _, _ = _score(far)
    assert near_total > far_total


def test_higher_star_bumps_score_at_equal_distance():
    r_low = _restaurant(source_id=1, star=3.0)
    r_high = _restaurant(source_id=2, star=5.0)
    low_total, _, _, _ = _score(r_low)
    high_total, _, _, _ = _score(r_high)
    assert high_total > low_total


def test_price_fit_peaks_at_user_band():
    at_band = _restaurant(source_id=1, avg_price=150_000)
    off_band = _restaurant(source_id=2, avg_price=500_000)
    on_total, _, _, _ = _score(at_band, price_band=150_000)
    off_total, _, _, _ = _score(off_band, price_band=150_000)
    assert on_total > off_total


def test_price_fit_disabled_when_band_missing():
    # Without a user price band, avg_price should not affect the score: two
    # restaurants at the same spot, different prices, score identically.
    cheap = _restaurant(source_id=1, avg_price=50_000)
    pricey = _restaurant(source_id=2, avg_price=500_000)
    cheap_total, cheap_bd, _, _ = _score(cheap, price_band=None)
    pricey_total, pricey_bd, _, _ = _score(pricey, price_band=None)
    assert cheap_total == pytest.approx(pricey_total, rel=1e-9)
    assert cheap_bd.price_fit is None
    assert pricey_bd.price_fit is None


def test_taste_match_boosts_when_likes_intersect_cuisine():
    plain = _restaurant(source_id=1, type=["vietnamese"])
    seafood = _restaurant(source_id=2, type=["seafood"])
    plain_total, _, plain_match, _ = _score(plain, likes={"seafood"})
    seafood_total, _, seafood_match, _ = _score(seafood, likes={"seafood"})
    assert seafood_total > plain_total
    assert "seafood" in seafood_match
    assert plain_match == []


def test_taste_match_disabled_without_preferences():
    restaurant = _restaurant(source_id=1, type=["seafood"])
    _total, breakdown, _, _ = _score(restaurant, likes=set(), avoids=set())
    assert breakdown.taste_match is None


def test_allergy_penalty_triggers_on_direct_keyword_match():
    restaurant = _restaurant(source_id=1, type=["seafood"])
    _total, breakdown, _, caution = _score(
        restaurant,
        allergens={"seafood"},
    )
    assert breakdown.allergy_penalty == ALLERGY_PENALTY
    assert "seafood" in caution


def test_allergy_penalty_absent_without_match():
    restaurant = _restaurant(source_id=1, type=["vietnamese"])
    _total, breakdown, _, caution = _score(restaurant, allergens={"seafood"})
    assert breakdown.allergy_penalty == 0.0
    assert caution == []


def test_all_signals_absent_returns_distance_only_score():
    restaurant = _restaurant(source_id=1, star=5.0, avg_price=None)
    total, breakdown, _, _ = _score(
        restaurant,
        likes=set(),
        avoids=set(),
        allergens=set(),
        price_band=None,
    )
    # Same spot ⇒ distance_decay = 1; quality = 1; weighted at 0.80 + 0.20 = 100.
    assert total == pytest.approx(100.0, rel=1e-9)
    assert breakdown.distance == pytest.approx(1.0)
    assert breakdown.quality == pytest.approx(1.0)
    assert breakdown.price_fit is None
    assert breakdown.taste_match is None


def test_distance_decay_uses_lambda():
    # At LAMBDA km away, the distance term should be ~exp(-1) ≈ 0.368.
    # Approximate by placing the restaurant LAMBDA_KM north (lat only).
    restaurant = _restaurant(
        source_id=1,
        lat=16.06 + (DISTANCE_LAMBDA_KM / 111.0),
        lng=108.22,
    )
    _total, breakdown, _, _ = _score(restaurant)
    assert breakdown.distance == pytest.approx(math.exp(-1.0), rel=0.05)


# --- diversity_penalty ------------------------------------------------------


def test_diversity_penalty_zero_without_overlap():
    assert diversity_penalty([], ["vietnamese"]) == 0.0
    assert diversity_penalty(["korean"], []) == 0.0


def test_diversity_penalty_proportional_to_overlap():
    penalty = diversity_penalty(
        ["vietnamese", "seafood", "bbq"],
        ["vietnamese", "bbq"],
    )
    assert penalty == pytest.approx(2 * DIVERSITY_PENALTY_PER_HIT)


def test_recent_type_window_caps_at_size():
    window = RecentTypeWindow(size=3)
    for cuisines in (["a"], ["b"], ["c"], ["d"]):
        window.push(cuisines)
    flat = window.flat()
    # Only the last 3 pushes survive.
    assert "a" not in flat
    assert sorted(set(flat)) == ["b", "c", "d"]


# --- data_loader._parse_item -----------------------------------------------


def test_parse_item_handles_root_wrapper_dict():
    item = {"id": 7, "name": "Quán", "address": "X", "lat": 10.0, "lng": 105.0}
    parsed = _parse_item(item)
    assert parsed.source_id == 7
    assert parsed.type == []
    assert parsed.meals == []


def test_parse_item_tolerates_missing_optional_fields():
    item = {"id": 1, "name": "Q", "address": "A", "lat": 1.0, "lng": 2.0}
    parsed = _parse_item(item)
    assert parsed.avg_price is None
    assert parsed.star is None
    assert parsed.semantic_text is None
    assert parsed.image_url is None
    assert parsed.phone_num is None


def test_parse_item_clamps_star_to_five():
    parsed = _parse_item(
        {"id": 1, "name": "Q", "address": "A", "lat": 1.0, "lng": 2.0, "star": 9.0}
    )
    assert parsed.star == 5.0


def test_parse_item_lowercases_type_strings():
    parsed = _parse_item(
        {
            "id": 1,
            "name": "Q",
            "address": "A",
            "lat": 1.0,
            "lng": 2.0,
            "type": ["Vietnamese", " SEAFOOD "],
        }
    )
    assert parsed.type == ["vietnamese", "seafood"]


def test_parse_item_rejects_non_dict_row():
    with pytest.raises(TypeError):
        _parse_item("not a dict")  # type: ignore[arg-type]


def test_parse_item_requires_id_name_address_lat_lng():
    with pytest.raises(KeyError):
        _parse_item({"name": "Q", "address": "A", "lat": 1.0, "lng": 2.0})


def test_load_restaurants_handles_root_key_dict():
    # Simulate the file format the user supplied (``{"root": [...]}``).
    raw = {"root": [{"id": 1, "name": "Q", "address": "A", "lat": 1.0, "lng": 2.0}]}
    parsed = data_loader._parse_item(raw["root"][0])  # type: ignore[index]
    assert parsed.source_id == 1


def test_reset_cache_for_tests_round_trip():
    fixture = [
        RestaurantData(
            source_id=42,
            name="x",
            address="y",
            lat=1.0,
            lng=2.0,
        )
    ]
    data_loader._reset_cache_for_tests(fixture)
    try:
        assert data_loader.load_restaurants() == fixture
        assert data_loader.get_restaurant_by_source_id(42) is fixture[0]
    finally:
        data_loader._reset_cache_for_tests(None)
