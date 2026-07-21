"""Pydantic schemas for the feed_recommend HTTP surface."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MealBrief(BaseModel):
    """One meal entry on a restaurant card.

    The JSON dataset's ``meals[]`` shape is not strictly enforced (it's
    hand-authored), so extra fields are ignored and ``name``/``price`` are
    optional — the UI skips entries lacking a name.
    """

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    price: int | None = None


class ScoreBreakdown(BaseModel):
    """Transparency into one restaurant's score so the UI can show "why".

    Disabled signals (no user price band, no preferences) are ``None`` so the
    UI can render the active ones only.
    """

    distance: float
    quality: float
    price_fit: float | None = None
    taste_match: float | None = None
    allergy_penalty: float
    total: float


class RestaurantCardResponse(BaseModel):
    """A restaurant as the feed returns it."""

    source_id: int
    name: str
    address: str
    lat: float
    lng: float
    avg_price: int | None = None
    star: float | None = None
    image_url: str | None = None
    phone_num: str | None = None
    type: list[str] = Field(default_factory=list)
    meals: list[MealBrief] = Field(default_factory=list)
    semantic_text: str | None = None
    distance_km: float | None = None
    score: float
    score_breakdown: ScoreBreakdown
    match_reasons: list[str] = Field(default_factory=list)
    caution_reasons: list[str] = Field(default_factory=list)
    saved: bool = False
    seen_action: str | None = None


class FeedResponse(BaseModel):
    items: list[RestaurantCardResponse]
    total_available: int
    location_source: str | None = None
    radius_km: float


class RestaurantSummaryResponse(BaseModel):
    """Lightweight restaurant reference used by ``dining_sessions`` echo.

    Built from the in-memory cache when the dining API serialises a session
    that has a ``restaurant_source_id``. No DB lookup involved.
    """

    source_id: int
    name: str
    address: str
    lat: float
    lng: float
    maps_url: str


class SetLocationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address_text: str | None = None
    source: Literal["geolocation", "manual"]


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lat: float
    lng: float
    address_text: str | None = None
    source: str
    updated_at: datetime


class MarkSeenRequest(BaseModel):
    action: Literal["skip", "view"]


class SaveRestaurantRequest(BaseModel):
    """Reserved for future per-save metadata (note, folder). Empty in v1."""

    note: str | None = None


def google_maps_url(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def meal_briefs_from_raw(meals: list[dict[str, Any]]) -> list[MealBrief]:
    """Coerce the raw ``meals[]`` JSON list into ``MealBrief``s.

    Skips entries that are not dicts or lack a ``name`` (the UI's contract is
    that a meal always has a name to display).
    """
    out: list[MealBrief] = []
    for raw in meals:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        price_raw = raw.get("price")
        price = int(price_raw) if isinstance(price_raw, (int, float)) else None
        out.append(MealBrief(name=name.strip(), price=price))
    return out
