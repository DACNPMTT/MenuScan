"""HTTP contract tests for dining session endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.dining.dependencies import get_dining_session_service
from src.modules.dining.exceptions import (
    DiningInviteInvalidError,
    DiningSessionClosedError,
    DiningSessionNotFoundError,
    DiningParticipantNotFoundError,
)
from src.modules.dining.models import (
    DiningSession,
    DiningSessionInvite,
    DiningSessionMode,
    DiningSessionParticipant,
    DiningSessionParticipantSelection,
    DiningSessionStatus,
)
from src.modules.menu.models import FoodItem, Menu, MenuHostSelection, MenuStatus
from src.modules.dining.schemas import DiningPreferenceRequest
from src.modules.dining.service import DiningSessionInviteBundle
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_SESSION_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_INVITE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_MENU_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
_ITEM_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
_PARTICIPANT_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")
_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


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


class StubDiningSessionService:
    def __init__(self) -> None:
        self.create_calls: list[dict[str, object]] = []
        self.join_calls: list[dict[str, object]] = []
        self.delete_calls: list[dict[str, object]] = []
        self.remove_calls: list[dict[str, object]] = []
        self.selection_calls: list[dict[str, object]] = []
        self.host_selection_calls: list[dict[str, object]] = []
        self.effect: Exception | None = None

    def create_session(
        self,
        user: User,
        *,
        mode: str,
        invite_expires_in_hours: int | None,
        name: str | None = None,
    ) -> DiningSessionInviteBundle:
        self.create_calls.append(
            {
                "user_id": user.id,
                "mode": mode,
                "invite_expires_in_hours": invite_expires_in_hours,
                "name": name,
            }
        )
        if self.effect:
            raise self.effect

        session = DiningSession(
            id=_SESSION_ID,
            name=name,
            created_by_user_id=user.id,
            mode=DiningSessionMode(mode),
            status=DiningSessionStatus.COLLECTING,
            created_at=_NOW,
            updated_at=_NOW,
        )
        invite = DiningSessionInvite(
            id=_INVITE_ID,
            dining_session_id=_SESSION_ID,
            token_hash="fakehash",
            expires_at=None,
            use_count=0,
            created_at=_NOW,
        )
        return DiningSessionInviteBundle(
            dining_session=session,
            invite=invite,
            invite_token="faketoken",
        )

    def list_sessions(self, user: User) -> list[DiningSession]:
        if self.effect:
            raise self.effect
        return [
            DiningSession(
                id=_SESSION_ID,
                created_by_user_id=user.id,
                mode=DiningSessionMode.GROUP,
                status=DiningSessionStatus.COLLECTING,
                created_at=_NOW,
                updated_at=_NOW,
            )
        ]

    def get_session(self, user: User, *, session_id: uuid.UUID) -> DiningSession:
        if self.effect:
            raise self.effect
        if session_id != _SESSION_ID:
            raise DiningSessionNotFoundError()
        return DiningSession(
            id=_SESSION_ID,
            created_by_user_id=user.id,
            mode=DiningSessionMode.GROUP,
            status=DiningSessionStatus.COLLECTING,
            created_at=_NOW,
            updated_at=_NOW,
            participants=[],
        )

    def get_public_session(self, *, invite_token: str) -> DiningSession:
        if self.effect:
            raise self.effect
        if invite_token != "faketoken":
            raise DiningInviteInvalidError()
        return DiningSession(
            id=_SESSION_ID,
            created_by_user_id=_USER_ID,
            mode=DiningSessionMode.GROUP,
            status=DiningSessionStatus.COLLECTING,
            created_at=_NOW,
            updated_at=_NOW,
            participants=[],
        )

    def join_with_invite(
        self,
        *,
        invite_token: str,
        display_name: str,
        preferences: list[DiningPreferenceRequest],
    ) -> DiningSessionParticipant:
        self.join_calls.append(
            {
                "invite_token": invite_token,
                "display_name": display_name,
                "preferences": preferences,
            }
        )
        if self.effect:
            raise self.effect
        if invite_token != "faketoken":
            raise DiningInviteInvalidError()
        return DiningSessionParticipant(
            id=uuid.uuid4(),
            dining_session_id=_SESSION_ID,
            display_name=display_name,
            joined_at=_NOW,
            preferences=[],
        )

    def delete_session(self, user: User, *, session_id: uuid.UUID) -> None:
        self.delete_calls.append({"user_id": user.id, "session_id": session_id})
        if self.effect:
            raise self.effect
        if session_id != _SESSION_ID:
            raise DiningSessionNotFoundError()

    def remove_participant(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> None:
        self.remove_calls.append(
            {
                "user_id": user.id,
                "session_id": session_id,
                "participant_id": participant_id,
            }
        )
        if self.effect:
            raise self.effect
        if session_id != _SESSION_ID:
            raise DiningSessionNotFoundError()
        if participant_id == uuid.UUID("00000000-0000-0000-0000-000000000000"):
            raise DiningParticipantNotFoundError()

    def get_host_selections(
        self,
        user: User,
        *,
        menu_id: uuid.UUID,
    ) -> list[MenuHostSelection]:
        if self.effect:
            raise self.effect
        return [
            MenuHostSelection(
                menu_id=menu_id,
                food_item_id=_ITEM_ID,
                quantity=2,
                note="ít cay",
            )
        ]

    def set_host_selections(
        self,
        user: User,
        *,
        menu_id: uuid.UUID,
        selections: list[object],
    ) -> list[object]:
        self.host_selection_calls.append(
            {"menu_id": menu_id, "selections": selections}
        )
        if self.effect:
            raise self.effect
        return list(selections)

    def set_participant_preferences(
        self,
        *,
        session_id: uuid.UUID,
        invite_token: str,
        participant_id: uuid.UUID,
        preferences: list[DiningPreferenceRequest],
    ) -> DiningSessionParticipant:
        if self.effect:
            raise self.effect
        if invite_token != "faketoken":
            raise DiningInviteInvalidError()
        return DiningSessionParticipant(
            id=participant_id,
            dining_session_id=_SESSION_ID,
            display_name="Guest A",
            joined_at=_NOW,
            preferences=[],
        )

    def set_session_closed(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
        closed: bool,
    ) -> DiningSession:
        if self.effect:
            raise self.effect
        if session_id != _SESSION_ID:
            raise DiningSessionNotFoundError()
        return DiningSession(
            id=_SESSION_ID,
            created_by_user_id=user.id,
            mode=DiningSessionMode.GROUP,
            status=(
                DiningSessionStatus.CLOSED
                if closed
                else DiningSessionStatus.COLLECTING
            ),
            created_at=_NOW,
            updated_at=_NOW,
            participants=[],
        )

    def list_session_meals(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
    ) -> list[tuple[Menu, int]]:
        if self.effect:
            raise self.effect
        if session_id != _SESSION_ID:
            raise DiningSessionNotFoundError()
        return [
            (
                Menu(
                    id=_MENU_ID,
                    title="Bún & Phở",
                    default_currency="VND",
                    status=MenuStatus.CONFIRMED,
                    created_at=_NOW,
                ),
                3,
            )
        ]

    def get_public_menu(
        self,
        *,
        session_id: uuid.UUID,
        invite_token: str,
    ) -> tuple[DiningSession, Menu | None, list[FoodItem]]:
        if self.effect:
            raise self.effect
        if invite_token != "faketoken":
            raise DiningInviteInvalidError()
        session = DiningSession(
            id=_SESSION_ID,
            created_by_user_id=_USER_ID,
            mode=DiningSessionMode.GROUP,
            status=DiningSessionStatus.COMPLETED,
            menu_id=_MENU_ID,
            created_at=_NOW,
            updated_at=_NOW,
        )
        menu = Menu(id=_MENU_ID, title="Bún & Phở", default_currency="VND")
        items = [
            FoodItem(
                id=_ITEM_ID,
                menu_id=_MENU_ID,
                original_name="Phở bò",
                translated_name="Beef Pho",
                price=Decimal("65000.00"),
                currency="VND",
                allergens=["gluten"],
            )
        ]
        return session, menu, items

    def set_participant_selections(
        self,
        *,
        session_id: uuid.UUID,
        invite_token: str,
        participant_id: uuid.UUID,
        selections: list[object],
    ) -> list[object]:
        self.selection_calls.append(
            {
                "session_id": session_id,
                "invite_token": invite_token,
                "participant_id": participant_id,
                "selections": selections,
            }
        )
        if self.effect:
            raise self.effect
        if invite_token != "faketoken":
            raise DiningInviteInvalidError()
        return list(selections)

    def get_selections_summary(
        self,
        user: User,
        *,
        session_id: uuid.UUID,
    ) -> DiningSession:
        if self.effect:
            raise self.effect
        if session_id != _SESSION_ID:
            raise DiningSessionNotFoundError()
        participant = DiningSessionParticipant(
            id=_PARTICIPANT_ID,
            dining_session_id=_SESSION_ID,
            display_name="Guest A",
            joined_at=_NOW,
            selections=[
                DiningSessionParticipantSelection(
                    food_item_id=_ITEM_ID,
                    quantity=2,
                    note="ít cay",
                    created_at=_NOW,
                    updated_at=_NOW,
                )
            ],
        )
        return DiningSession(
            id=_SESSION_ID,
            created_by_user_id=user.id,
            mode=DiningSessionMode.GROUP,
            status=DiningSessionStatus.COMPLETED,
            created_at=_NOW,
            updated_at=_NOW,
            participants=[participant],
        )


def _make_client(
    stub: StubDiningSessionService,
    user: User | None = None,
) -> TestClient:
    app = create_app(
        application_settings=_settings(),
        database_engine=Mock(),
    )
    app.dependency_overrides[get_dining_session_service] = lambda: stub
    if user:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def test_create_session_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.post(
        "/api/v1/dining/sessions",
        json={
            "mode": "GROUP",
            "invite_expires_in_hours": 24,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["invite_token"] == "faketoken"
    assert body["data"]["session"]["id"] == str(_SESSION_ID)
    assert body["data"]["session"]["mode"] == "GROUP"
    assert stub.create_calls == [
        {
            "user_id": _USER_ID,
            "mode": "GROUP",
            "invite_expires_in_hours": 24,
            "name": None,
        }
    ]


def test_list_sessions_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.get("/api/v1/dining/sessions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(_SESSION_ID)


def test_get_session_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.get(f"/api/v1/dining/sessions/{_SESSION_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == str(_SESSION_ID)


def test_get_session_not_found():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/dining/sessions/{random_id}")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DINING_SESSION_NOT_FOUND"


def test_get_public_session_success():
    stub = StubDiningSessionService()
    client = _make_client(stub)  # No auth needed for public

    response = client.get("/api/v1/dining/public/sessions?invite_token=faketoken")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["session_id"] == str(_SESSION_ID)
    assert body["data"]["mode"] == "GROUP"


def test_get_public_session_invalid_token():
    stub = StubDiningSessionService()
    client = _make_client(stub)

    response = client.get("/api/v1/dining/public/sessions?invite_token=badtoken")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DINING_INVITE_INVALID"


def test_join_session_success():
    stub = StubDiningSessionService()
    client = _make_client(stub)

    payload = {
        "display_name": "Guest User",
        "preferences": [
            {
                "code": "gluten",
                "category": "allergen",
                "preference_type": "ALLERGY",
                "importance": 5,
            }
        ],
    }
    response = client.post(
        "/api/v1/dining/public/sessions/join?invite_token=faketoken",
        json=payload,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["display_name"] == "Guest User"
    assert len(stub.join_calls) == 1
    assert stub.join_calls[0]["invite_token"] == "faketoken"
    assert stub.join_calls[0]["display_name"] == "Guest User"
    assert stub.join_calls[0]["preferences"][0].code == "gluten"


def test_join_session_closed():
    stub = StubDiningSessionService()
    stub.effect = DiningSessionClosedError()
    client = _make_client(stub)

    payload = {"display_name": "Guest User", "preferences": []}
    response = client.post(
        "/api/v1/dining/public/sessions/join?invite_token=faketoken",
        json=payload,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DINING_SESSION_CLOSED"


def test_delete_session_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.delete(f"/api/v1/dining/sessions/{_SESSION_ID}")

    assert response.status_code == 204
    assert stub.delete_calls == [{"user_id": _USER_ID, "session_id": _SESSION_ID}]


def test_delete_session_not_found():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    random_id = uuid.uuid4()
    response = client.delete(f"/api/v1/dining/sessions/{random_id}")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DINING_SESSION_NOT_FOUND"


def test_remove_participant_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    p_id = uuid.uuid4()
    response = client.delete(
        f"/api/v1/dining/sessions/{_SESSION_ID}/participants/{p_id}"
    )

    assert response.status_code == 204
    assert stub.remove_calls == [
        {
            "user_id": _USER_ID,
            "session_id": _SESSION_ID,
            "participant_id": p_id,
        }
    ]


def test_remove_participant_not_found():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    p_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    response = client.delete(
        f"/api/v1/dining/sessions/{_SESSION_ID}/participants/{p_id}"
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DINING_PARTICIPANT_NOT_FOUND"


def test_set_participant_preferences_success():
    stub = StubDiningSessionService()
    client = _make_client(stub)

    payload = {
        "participant_id": str(_PARTICIPANT_ID),
        "preferences": [
            {
                "code": "peanut",
                "category": "allergen",
                "preference_type": "ALLERGY",
                "importance": 5,
            }
        ],
    }
    response = client.put(
        f"/api/v1/dining/public/sessions/{_SESSION_ID}/preferences?invite_token=faketoken",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_get_host_selections_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.get(f"/api/v1/dining/menus/{_MENU_ID}/host-selections")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["menu_id"] == str(_MENU_ID)
    assert body["data"]["items"][0]["food_item_id"] == str(_ITEM_ID)
    assert body["data"]["items"][0]["quantity"] == 2


def test_set_host_selections_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    payload = {
        "selections": [{"food_item_id": str(_ITEM_ID), "quantity": 3, "note": None}],
    }
    response = client.put(
        f"/api/v1/dining/menus/{_MENU_ID}/host-selections", json=payload
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated"] == 1
    assert len(stub.host_selection_calls) == 1
    assert stub.host_selection_calls[0]["selections"][0].food_item_id == _ITEM_ID


def test_list_session_meals_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.get(f"/api/v1/dining/sessions/{_SESSION_ID}/meals")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 1
    assert items[0]["menu_id"] == str(_MENU_ID)
    assert items[0]["item_count"] == 3
    assert items[0]["title"] == "Bún & Phở"


def test_close_session_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.post(f"/api/v1/dining/sessions/{_SESSION_ID}/close")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "CLOSED"


def test_open_session_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.post(f"/api/v1/dining/sessions/{_SESSION_ID}/open")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "COLLECTING"


def test_close_session_not_found():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.post(f"/api/v1/dining/sessions/{uuid.uuid4()}/close")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DINING_SESSION_NOT_FOUND"


def test_get_public_session_menu_success():
    stub = StubDiningSessionService()
    client = _make_client(stub)  # auth-free, gated by invite token

    response = client.get(
        f"/api/v1/dining/public/sessions/{_SESSION_ID}/menu?invite_token=faketoken"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["menu_id"] == str(_MENU_ID)
    assert body["data"]["title"] == "Bún & Phở"
    items = body["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(_ITEM_ID)
    assert items[0]["price"] == "65000.00"
    assert items[0]["allergens"] == ["gluten"]


def test_get_public_session_menu_invalid_token():
    stub = StubDiningSessionService()
    client = _make_client(stub)

    response = client.get(
        f"/api/v1/dining/public/sessions/{_SESSION_ID}/menu?invite_token=badtoken"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DINING_INVITE_INVALID"


def test_set_participant_selections_success():
    stub = StubDiningSessionService()
    client = _make_client(stub)

    payload = {
        "participant_id": str(_PARTICIPANT_ID),
        "selections": [
            {"food_item_id": str(_ITEM_ID), "quantity": 2, "note": "ít cay"},
        ],
    }
    response = client.put(
        f"/api/v1/dining/public/sessions/{_SESSION_ID}/selections?invite_token=faketoken",
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["updated"] == 1
    assert len(stub.selection_calls) == 1
    call = stub.selection_calls[0]
    assert call["participant_id"] == _PARTICIPANT_ID
    assert call["selections"][0].food_item_id == _ITEM_ID
    assert call["selections"][0].quantity == 2
    assert call["selections"][0].note == "ít cay"


def test_set_participant_selections_rejects_zero_quantity():
    stub = StubDiningSessionService()
    client = _make_client(stub)

    payload = {
        "participant_id": str(_PARTICIPANT_ID),
        "selections": [{"food_item_id": str(_ITEM_ID), "quantity": 0}],
    }
    response = client.put(
        f"/api/v1/dining/public/sessions/{_SESSION_ID}/selections?invite_token=faketoken",
        json=payload,
    )

    assert response.status_code == 400  # validation: quantity >= 1


def test_get_session_selections_summary_success():
    stub = StubDiningSessionService()
    user = User(id=_USER_ID, email="host@example.com")
    client = _make_client(stub, user)

    response = client.get(f"/api/v1/dining/sessions/{_SESSION_ID}/selections")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 1
    assert items[0]["food_item_id"] == str(_ITEM_ID)
    assert items[0]["total_quantity"] == 2
    assert items[0]["selected_by"][0]["display_name"] == "Guest A"
    assert items[0]["selected_by"][0]["quantity"] == 2
    assert items[0]["selected_by"][0]["note"] == "ít cay"


def test_score_item_for_diner_rules():
    from src.modules.dining.service import DiningSessionService
    from src.modules.menu.models import FoodItem
    from src.modules.identity.models import FoodProfilePreference
    from src.modules.identity.models import PreferenceType
    from src.modules.dining.models import RecommendationVerdict

    # Test allergy avoidance
    item = FoodItem(
        original_name="Peanut Butter Cookies",
        allergens=["peanut"],
        dietary_tags=[],
    )
    pref = FoodProfilePreference(
        code="peanut",
        preference_type=PreferenceType.ALLERGY,
    )

    verdict, score, fit, risk = DiningSessionService._score_item_for_diner(item, [pref])
    assert verdict == RecommendationVerdict.AVOID
    assert score == 0.0
    assert "Dị ứng với peanut" in risk

    # Test liked tag boosts score
    item2 = FoodItem(
        original_name="Spicy Beef Noodles",
        allergens=[],
        dietary_tags=["contains_beef"],
    )
    pref2 = FoodProfilePreference(
        code="Beef",
        preference_type=PreferenceType.LIKE,
    )

    verdict2, score2, fit2, risk2 = DiningSessionService._score_item_for_diner(
        item2, [pref2]
    )
    assert verdict2 == RecommendationVerdict.RECOMMENDED
    assert score2 == 100.0
    assert "Phù hợp vì bạn beef" in fit2
