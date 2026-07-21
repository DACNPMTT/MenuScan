"""FastAPI router for the Discovery feed."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.core.responses import success_response
from src.modules.feed_recommend.dependencies import get_feed_recommend_service
from src.modules.feed_recommend.schemas import (
    LocationResponse,
    MarkSeenRequest,
    SaveRestaurantRequest,
    SetLocationRequest,
)
from src.modules.feed_recommend.service import FeedRecommendService
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("")
def get_feed(
    radius_km: float = Query(default=5.0, ge=0.1, le=100.0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """Top-N scored restaurant cards, excluding already-saved and already-seen."""
    response = service.get_feed(current_user, radius_km=radius_km, limit=limit)
    return success_response(data=response.model_dump(mode="json"))


@router.post("/{restaurant_source_id}/seen")
def mark_seen(
    restaurant_source_id: int,
    payload: MarkSeenRequest,
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """Mark a restaurant as seen (skip or view). Idempotent."""
    service.mark_seen(current_user, restaurant_source_id, payload)
    return success_response(data={"ok": True})


@router.post(
    "/saves/{restaurant_source_id}",
    status_code=status.HTTP_201_CREATED,
)
def save_restaurant(
    restaurant_source_id: int,
    _payload: SaveRestaurantRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """Bookmark a restaurant. Also marks it as seen so it leaves the feed."""
    card = service.save_restaurant(current_user, restaurant_source_id)
    return success_response(data=card.model_dump(mode="json"))


@router.delete(
    "/saves/{restaurant_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unsave_restaurant(
    restaurant_source_id: int,
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> None:
    """Remove a restaurant from the user's saved list. Idempotent."""
    service.unsave_restaurant(current_user, restaurant_source_id)


@router.get("/saves")
def list_saved(
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """All saved restaurants for the current user, newest save first."""
    cards = service.list_saved(current_user)
    return success_response(data=[c.model_dump(mode="json") for c in cards])


@router.get("/restaurants/{restaurant_source_id}")
def get_restaurant_detail(
    restaurant_source_id: int,
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """One restaurant's full detail (with per-user score & saved flag)."""
    card = service.get_restaurant_detail(current_user, restaurant_source_id)
    return success_response(data=card.model_dump(mode="json"))


@router.get("/me/location")
def get_location(
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """Return the user's saved location, or ``null`` if not yet set."""
    location: LocationResponse | None = service.get_location(current_user)
    data = location.model_dump(mode="json") if location is not None else None
    return success_response(data=data)


@router.put("/me/location")
def set_location(
    payload: SetLocationRequest,
    current_user: User = Depends(get_current_user),
    service: FeedRecommendService = Depends(get_feed_recommend_service),
) -> dict[str, object]:
    """Insert or replace the user's location (geolocation or manual)."""
    location = service.set_location(current_user, payload)
    return success_response(data=location.model_dump(mode="json"))
