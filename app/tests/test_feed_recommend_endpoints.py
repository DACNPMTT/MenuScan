"""HTTP contract tests for the Discovery feed endpoints.

Uses a stubbed ``FeedRecommendService`` (no DB) and a synthetic in-memory
dataset injected via ``data_loader._reset_cache_for_tests``. This keeps the
test hermetic — no JSON file or Postgres required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.feed_recommend import data_loader
from src.modules.feed_recommend.data_loader import RestaurantData
from src.modules.feed_recommend.dependencies import get_feed_recommend_service
from src.modules.feed_recommend.exceptions import (
    AlreadySavedError,
    LocationNotSetError,
    RestaurantNotFoundError,
)
from src.modules.feed_recommend.schemas import (
    FeedResponse,
    LocationResponse,
    RestaurantCardResponse,
    ScoreBreakdown,
)
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


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


def _restaurant(
    *,
    source_id: int,
    lat: float = 16.06,
    lng: float = 108.22,
    star: float = 4.5,
    avg_price: int | None = 100_000,
    type: list[str] | None = None,
) -> RestaurantData:
    return RestaurantData(
        source_id=source_id,
        name=f"Quán {source_id}",
        address="Đà Nẵng",
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


_FIXTURE_RESTAURANTS = [
    _restaurant(source_id=1, lat=16.060, lng=108.220, star=4.8, type=["vietnamese"]),
    _restaurant(source_id=2, lat=16.100, lng=108.250, star=4.0, type=["seafood"]),
    _restaurant(source_id=3, lat=16.200, lng=108.300, star=4.6, type=["korean"]),
    _restaurant(source_id=4, lat=16.060, lng=108.221, star=4.5, type=["vietnamese"]),
    _restaurant(source_id=5, lat=16.061, lng=108.222, star=4.2, type=["bbq"]),
]
_FIXTURE_IDS = {r.source_id for r in _FIXTURE_RESTAURANTS}


def _card(
    r: RestaurantData,
    *,
    score: float,
    saved: bool = False,
    seen_action: str | None = None,
    distance_km: float = 1.0,
) -> RestaurantCardResponse:
    return RestaurantCardResponse(
        source_id=r.source_id,
        name=r.name,
        address=r.address,
        lat=r.lat,
        lng=r.lng,
        avg_price=r.avg_price,
        star=r.star,
        image_url=None,
        phone_num=None,
        type=list(r.type),
        meals=[],
        semantic_text=None,
        distance_km=distance_km,
        score=score,
        score_breakdown=ScoreBreakdown(
            distance=0.9,
            quality=0.9,
            price_fit=None,
            taste_match=None,
            allergy_penalty=0.0,
            total=score,
        ),
        match_reasons=[],
        caution_reasons=[],
        saved=saved,
        seen_action=seen_action,
    )


class StubFeedRecommendService:
    """Records every call and returns canned responses.

    Endpoint contracts are what we test here — the scorer has its own unit
    test file. The stub raises the same ApplicationError subclasses the real
    service does so the wire shape match production.
    """

    def __init__(self) -> None:
        self.feed_calls: list[dict[str, Any]] = []
        self.mark_seen_calls: list[dict[str, Any]] = []
        self.save_calls: list[dict[str, Any]] = []
        self.unsave_calls: list[dict[str, Any]] = []
        self.list_saved_calls: list[dict[str, Any]] = []
        self.detail_calls: list[dict[str, Any]] = []
        self.get_location_calls: list[dict[str, Any]] = []
        self.set_location_calls: list[dict[str, Any]] = []
        self.location: LocationResponse | None = None
        self.saved_source_ids: set[int] = set()
        self.seen_source_ids: set[int] = set()

    def _find(self, source_id: int) -> RestaurantData:
        return next(r for r in _FIXTURE_RESTAURANTS if r.source_id == source_id)

    def get_feed(self, user, *, radius_km: float = 5.0, limit: int = 20) -> FeedResponse:
        self.feed_calls.append(
            {"user_id": user.id, "radius_km": radius_km, "limit": limit}
        )
        if self.location is None:
            raise LocationNotSetError()
        items = [
            _card(r, score=80.0 - r.source_id)
            for r in _FIXTURE_RESTAURANTS
            if r.source_id not in self.seen_source_ids
            and r.source_id not in self.saved_source_ids
        ][:limit]
        return FeedResponse(
            items=items,
            total_available=len(items),
            location_source=self.location.source,
            radius_km=radius_km,
        )

    def mark_seen(self, user, restaurant_source_id: int, payload) -> None:
        self.mark_seen_calls.append(
            {
                "user_id": user.id,
                "restaurant_source_id": restaurant_source_id,
                "action": payload.action,
            }
        )
        if restaurant_source_id not in _FIXTURE_IDS:
            raise RestaurantNotFoundError(source_id=restaurant_source_id)
        self.seen_source_ids.add(restaurant_source_id)

    def save_restaurant(self, user, restaurant_source_id: int) -> RestaurantCardResponse:
        self.save_calls.append(
            {"user_id": user.id, "restaurant_source_id": restaurant_source_id}
        )
        if restaurant_source_id not in _FIXTURE_IDS:
            raise RestaurantNotFoundError(source_id=restaurant_source_id)
        if restaurant_source_id in self.saved_source_ids:
            raise AlreadySavedError()
        self.saved_source_ids.add(restaurant_source_id)
        return _card(self._find(restaurant_source_id), score=70.0, saved=True, seen_action="view")

    def unsave_restaurant(self, user, restaurant_source_id: int) -> None:
        self.unsave_calls.append(
            {"user_id": user.id, "restaurant_source_id": restaurant_source_id}
        )
        self.saved_source_ids.discard(restaurant_source_id)

    def list_saved(self, user) -> list[RestaurantCardResponse]:
        self.list_saved_calls.append({"user_id": user.id})
        return [
            _card(self._find(sid), score=70.0, saved=True)
            for sid in sorted(self.saved_source_ids)
        ]

    def get_restaurant_detail(self, user, restaurant_source_id: int) -> RestaurantCardResponse:
        self.detail_calls.append(
            {"user_id": user.id, "restaurant_source_id": restaurant_source_id}
        )
        if restaurant_source_id not in _FIXTURE_IDS:
            raise RestaurantNotFoundError(source_id=restaurant_source_id)
        return _card(self._find(restaurant_source_id), score=70.0)

    def get_location(self, user) -> LocationResponse | None:
        self.get_location_calls.append({"user_id": user.id})
        return self.location

    def set_location(self, user, payload) -> LocationResponse:
        self.set_location_calls.append(
            {
                "user_id": user.id,
                "lat": payload.lat,
                "lng": payload.lng,
                "address_text": payload.address_text,
                "source": payload.source,
            }
        )
        self.location = LocationResponse(
            lat=payload.lat,
            lng=payload.lng,
            address_text=payload.address_text,
            source=payload.source,
            updated_at=_NOW,
        )
        return self.location


def _make_client(stub: StubFeedRecommendService, user: User | None = None) -> TestClient:
    app = create_app(application_settings=_settings(), database_engine=Mock())
    app.dependency_overrides[get_feed_recommend_service] = lambda: stub
    if user:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset_dataset_cache():
    """Inject the synthetic 5-row dataset for every test.

    Cleared after the test so a later module that reads the cache does not
    see stale fixtures.
    """
    data_loader._reset_cache_for_tests(list(_FIXTURE_RESTAURANTS))
    yield
    data_loader._reset_cache_for_tests(None)


def _user() -> User:
    return User(id=_USER_ID, email="diner@example.com")


# --- GET /feed ---------------------------------------------------------------


def test_feed_without_location_returns_400_location_not_set():
    stub = StubFeedRecommendService()  # location is None
    client = _make_client(stub, _user())

    response = client.get("/api/v1/feed")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "LOCATION_NOT_SET"


def test_feed_after_setting_location_returns_ranked_cards():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    put = client.put(
        "/api/v1/feed/me/location",
        json={"lat": 16.06, "lng": 108.22, "source": "geolocation"},
    )
    assert put.status_code == 200

    response = client.get("/api/v1/feed?radius_km=5&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 5
    # Score is 80 - source_id (canned) so source 1 ranks first.
    assert items[0]["source_id"] == 1
    scores = [item["score"] for item in items]
    assert scores == sorted(scores, reverse=True)
    assert body["data"]["location_source"] == "geolocation"


# --- POST /feed/{id}/seen ----------------------------------------------------


def test_mark_seen_excludes_from_next_feed():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())
    client.put(
        "/api/v1/feed/me/location",
        json={"lat": 16.06, "lng": 108.22, "source": "geolocation"},
    )

    seen = client.post("/api/v1/feed/1/seen", json={"action": "skip"})
    assert seen.status_code == 200

    response = client.get("/api/v1/feed")
    items = response.json()["data"]["items"]
    assert all(item["source_id"] != 1 for item in items)


def test_mark_seen_unknown_restaurant_returns_404():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.post("/api/v1/feed/999999/seen", json={"action": "skip"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESTAURANT_NOT_FOUND"


# --- POST /feed/saves/{id} ---------------------------------------------------


def test_save_then_list_includes_it():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    saved = client.post("/api/v1/feed/saves/2")
    assert saved.status_code == 201
    assert saved.json()["data"]["source_id"] == 2

    listing = client.get("/api/v1/feed/saves")
    assert listing.status_code == 200
    assert any(item["source_id"] == 2 for item in listing.json()["data"])


def test_double_save_returns_409():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    first = client.post("/api/v1/feed/saves/3")
    second = client.post("/api/v1/feed/saves/3")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "RESTAURANT_ALREADY_SAVED"


def test_save_unknown_restaurant_returns_404():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.post("/api/v1/feed/saves/999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESTAURANT_NOT_FOUND"


def test_unsave_removes_from_list():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    client.post("/api/v1/feed/saves/4")
    response = client.delete("/api/v1/feed/saves/4")

    assert response.status_code == 204
    listing = client.get("/api/v1/feed/saves")
    assert all(item["source_id"] != 4 for item in listing.json()["data"])


# --- GET /feed/restaurants/{id} ---------------------------------------------


def test_get_restaurant_detail_returns_card():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.get("/api/v1/feed/restaurants/1")

    assert response.status_code == 200
    assert response.json()["data"]["source_id"] == 1


def test_get_restaurant_detail_unknown_returns_404():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.get("/api/v1/feed/restaurants/999999")

    assert response.status_code == 404


# --- Location ---------------------------------------------------------------


def test_get_location_returns_null_when_unset():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.get("/api/v1/feed/me/location")

    assert response.status_code == 200
    assert response.json()["data"] is None


def test_put_location_persists_and_echoes():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.put(
        "/api/v1/feed/me/location",
        json={
            "lat": 16.0544,
            "lng": 108.2022,
            "address_text": "Đà Nẵng",
            "source": "manual",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["lat"] == 16.0544
    assert data["lng"] == 108.2022
    assert data["source"] == "manual"
    assert data["address_text"] == "Đà Nẵng"


def test_put_location_rejects_out_of_range_lat():
    stub = StubFeedRecommendService()
    client = _make_client(stub, _user())

    response = client.put(
        "/api/v1/feed/me/location",
        json={"lat": 999.0, "lng": 0.0, "source": "geolocation"},
    )

    # App wraps validation errors as 400 (see core/errors.py).
    assert response.status_code in {400, 422}


# --- Group bridge: POST /dining/sessions ------------------------------------


def test_create_dining_session_with_restaurant_source_id():
    """Group-bridge: a session created from a Discovery card echoes the id."""
    from src.modules.dining.dependencies import get_dining_session_service
    from src.modules.dining.models import (
        DiningSession,
        DiningSessionInvite,
        DiningSessionMode,
        DiningSessionStatus,
    )
    from src.modules.dining.service import DiningSessionInviteBundle

    session_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    invite_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    now = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)

    class Stub:
        def create_session(
            self,
            user,
            *,
            mode,
            invite_expires_in_hours,
            name=None,
            restaurant_source_id=None,
        ):
            session = DiningSession(
                id=session_id,
                name=name,
                created_by_user_id=user.id,
                mode=DiningSessionMode(mode),
                status=DiningSessionStatus.COLLECTING,
                restaurant_source_id=restaurant_source_id,
                created_at=now,
                updated_at=now,
            )
            invite = DiningSessionInvite(
                id=invite_id,
                dining_session_id=session_id,
                token_hash="hash",
                expires_at=None,
                use_count=0,
                created_at=now,
            )
            return DiningSessionInviteBundle(
                dining_session=session,
                invite=invite,
                invite_token="rawtoken",
            )

    app = create_app(application_settings=_settings(), database_engine=Mock())
    app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_dining_session_service] = lambda: Stub()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/dining/sessions",
        json={"mode": "GROUP", "restaurant_source_id": 1},
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["session"]["restaurant_source_id"] == 1
    # The summary is populated from the in-memory cache.
    assert body["session"]["restaurant"]["source_id"] == 1
    assert body["session"]["restaurant"]["name"] == "Quán 1"
    assert "google.com/maps" in body["session"]["restaurant"]["maps_url"]


def test_create_dining_session_unknown_restaurant_returns_404():
    """Invalid restaurant_source_id is rejected before the session is created."""
    from src.modules.dining.dependencies import get_dining_session_service
    from src.modules.dining.service import DiningSessionService

    # Use the REAL service so the validation kicks in; DB commit will fail
    # after the raise, but we never reach the commit.
    app = create_app(application_settings=_settings(), database_engine=Mock())
    app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_dining_session_service] = lambda: DiningSessionService.__new__(
        DiningSessionService
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/dining/sessions",
        json={"mode": "GROUP", "restaurant_source_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESTAURANT_NOT_FOUND"
