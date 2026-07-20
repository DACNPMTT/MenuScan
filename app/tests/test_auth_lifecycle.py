import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.database import get_db
from src.modules.identity.models import (
    User,
    MagicLinkToken,
    UserSession,
    UserStatus,
    UserRole,
)
from src.modules.identity.service import hash_token, SESSION_TTL
from tests.conftest import FakeClock

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="PostgreSQL integration tests require RUN_DATABASE_TESTS=1",
)


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock(start=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    monkeypatch.setattr("src.modules.identity.service._utcnow", c)
    return c


@pytest.fixture
def client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_magic_link_verification_happy_path(client, db_session, clock):
    # Arrange: Create token in DB
    email = "new-user@example.com"
    raw_token = "token-12345"
    ml_token = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
    )
    db_session.add(ml_token)
    db_session.commit()

    # Act: Verify magic link
    response = client.post(
        "/api/v1/auth/magic-links/verify",
        json={"token": raw_token},
    )

    # Assert: Status 200 and standard envelope
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "USER"

    # Assert: Cookie is set with correct attributes
    assert "refresh_token" in response.cookies
    cookie_val = response.cookies["refresh_token"]
    assert "." in cookie_val

    # Assert: User created in ACTIVE state
    user = db_session.query(User).filter_by(email=email).first()
    assert user is not None
    assert user.status == UserStatus.ACTIVE

    # Assert: MagicLinkToken marked consumed
    db_session.refresh(ml_token)
    assert ml_token.consumed_at is not None
    assert ml_token.user_id == user.id

    # Assert: Session created
    session_id_str = cookie_val.split(".")[0]
    session_rec = (
        db_session.query(UserSession).filter_by(id=uuid.UUID(session_id_str)).first()
    )
    assert session_rec is not None
    assert session_rec.user_id == user.id
    assert session_rec.revoked_at is None


def test_magic_link_verification_fails_if_already_consumed(client, db_session, clock):
    # Arrange: Create consumed token in DB
    email = "consumed@example.com"
    raw_token = "token-consumed"
    ml_token = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
        consumed_at=clock(),
    )
    db_session.add(ml_token)
    db_session.commit()

    # Act: Verify magic link
    response = client.post(
        "/api/v1/auth/magic-links/verify",
        json={"token": raw_token},
    )

    # Assert: 400 INVALID_MAGIC_LINK
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_MAGIC_LINK"


def test_magic_link_verification_fails_if_expired(client, db_session, clock):
    # Arrange: Create token in DB
    email = "expired@example.com"
    raw_token = "token-expired"
    ml_token = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
    )
    db_session.add(ml_token)
    db_session.commit()

    # Advance clock beyond expiration
    clock.advance(minutes=16)

    # Act: Verify magic link
    response = client.post(
        "/api/v1/auth/magic-links/verify",
        json={"token": raw_token},
    )

    # Assert: 401 MAGIC_LINK_EXPIRED
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "MAGIC_LINK_EXPIRED"


def test_magic_link_verification_refuses_disabled_user(client, db_session, clock):
    """A previously-disabled/deleted user must not be silently re-activated by
    clicking a magic link — the account stays closed until an admin restores
    it. The magic link must be refused with 401 UNAUTHORIZED."""
    email = "disabled@example.com"
    user = User(
        email=email,
        status=UserStatus.DISABLED,
        role=UserRole.USER,
        deleted_at=clock(),
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    raw_token = "token-disabled"
    ml_token = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
    )
    db_session.add(ml_token)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/magic-links/verify",
        json={"token": raw_token},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    # User remains disabled, no session created.
    assert user.status == UserStatus.DISABLED
    assert db_session.query(UserSession).count() == 0


def test_refresh_token_rotation_happy_path(client, db_session, clock):
    # Arrange: Create User and Active Session in DB
    user = User(email="active@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-xyz"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    # Set cookie in client
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")

    # Advance time slightly
    clock.advance(hours=1)

    # Act: Refresh token
    response = client.post("/api/v1/auth/refresh")

    # Assert: 200, access token returned, new refresh cookie set
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]

    assert "refresh_token" in response.cookies
    new_cookie_val = response.cookies["refresh_token"]
    assert new_cookie_val != f"{session_id}.{raw_secret}"

    # Assert: DB updated with new hash and last rotated timestamp
    db_session.refresh(user_session)
    assert user_session.refresh_token_hash == hash_token(new_cookie_val.split(".")[1])
    assert user_session.last_rotated_at == clock()


def test_refresh_token_reuse_revokes_session_chain(client, db_session, clock):
    # Arrange: Create User and Active Session in DB
    user = User(email="reuse@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-1"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    # First rotation: Use secret-1, rotate to secret-2
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    res1 = client.post("/api/v1/auth/refresh")
    assert res1.status_code == 200
    secret_2 = res1.cookies["refresh_token"].split(".")[1]
    assert secret_2 != raw_secret

    # Advance past REFRESH_GRACE_WINDOW so the replay isn't mistaken for a
    # concurrent refresh from another tab. Inside the window the backend
    # returns SESSION_EXPIRED without revoking (multi-tab safety net).
    clock.advance(seconds=31)

    # Replay attack: Use secret-1 again
    db_session.expire_all()
    client.cookies.clear()
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    res2 = client.post("/api/v1/auth/refresh")

    # Assert: 401 SESSION_REVOKED
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "SESSION_REVOKED"

    # Assert: DB session has been revoked
    db_session.refresh(user_session)
    assert user_session.revoked_at is not None


def test_concurrent_refresh_within_grace_does_not_revoke(client, db_session, clock):
    """Multi-tab safety net: a refresh using the pre-rotation cookie within
    REFRESH_GRACE_WINDOW is treated as a concurrent refresh from another tab,
    not a replay attack. The session is NOT revoked — the caller gets 401
    SESSION_EXPIRED so it retries with the rotated cookie the browser has
    already stored."""
    user = User(email="grace@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-grace"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    # First rotation: rotate to secret-2.
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    res1 = client.post("/api/v1/auth/refresh")
    assert res1.status_code == 200

    # Within grace window: replay the pre-rotation cookie (as a second tab
    # racing with the first would). 10s < REFRESH_GRACE_WINDOW(30s).
    clock.advance(seconds=10)
    db_session.expire_all()
    client.cookies.clear()
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    res2 = client.post("/api/v1/auth/refresh")

    # Assert: 401 SESSION_EXPIRED (not SESSION_REVOKED), session still active.
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "SESSION_EXPIRED"
    db_session.refresh(user_session)
    assert user_session.revoked_at is None, (
        "Session must NOT be revoked within the grace window — that would "
        "log the user out of every tab when two tabs race on refresh."
    )


def test_refresh_fails_if_session_expired(client, db_session, clock):
    # Arrange: Create User and Session in DB
    user = User(email="expired-session@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-exp"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    # Advance clock past 30 days
    clock.advance(days=31)

    # Act: Refresh token
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    response = client.post("/api/v1/auth/refresh")

    # Assert: 401 SESSION_EXPIRED
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_refresh_survives_access_token_expiry(client, db_session, clock):
    """Regression: a session established via the verify endpoint must remain
    refreshable after ACCESS_TOKEN_TTL elapses. Before SESSION_TTL was bumped
    from 15 minutes to 30 days, the refresh token expired at the same instant
    as the access token — so the first 401/auto-refresh silently logged the
    user out. This test would have caught that bug."""
    email = "regression-auto-out@example.com"
    raw_token = "raw-magic-link-token-for-regression"
    ml_token = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
    )
    db_session.add(ml_token)
    db_session.commit()

    # Verify the magic link — the service establishes the session, so this
    # exercises the real expires_at assignment, not a hand-seeded row.
    verify_res = client.post(
        "/api/v1/auth/magic-links/verify",
        json={"token": raw_token},
    )
    assert verify_res.status_code == 200
    refresh_cookie = verify_res.cookies["refresh_token"]

    # The session row must live for SESSION_TTL, not ACCESS_TOKEN_TTL.
    session = db_session.query(UserSession).filter_by(user_id=db_session.query(User).filter_by(email=email).one().id).one()
    assert session.expires_at - session.created_at == SESSION_TTL

    # Advance past access-token expiry (15 min) but well within SESSION_TTL.
    clock.advance(minutes=20)

    # Refresh must succeed — the session is still alive.
    client.cookies.set("refresh_token", refresh_cookie)
    refresh_res = client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    body = refresh_res.json()
    assert body["success"] is True
    assert "access_token" in body["data"]


def test_refresh_slides_session_window(client, db_session, clock):
    """Each successful refresh must extend expires_at by SESSION_TTL (capped at
    SESSION_ABSOLUTE_TIMEOUT from creation), so active users don't get logged
    out after 30 days of continuous use."""
    from src.modules.identity.service import SESSION_ABSOLUTE_TIMEOUT

    user = User(email="sliding@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-slide"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    original_expiry = user_session.expires_at

    # Advance 1 day, then refresh.
    clock.advance(days=1)
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 200

    db_session.refresh(user_session)
    # Expiry slid forward by ~1 day (now + SESSION_TTL > original_expiry).
    assert user_session.expires_at > original_expiry
    # Sliding is capped at created_at + SESSION_ABSOLUTE_TIMEOUT.
    assert user_session.expires_at <= user_session.created_at + SESSION_ABSOLUTE_TIMEOUT


def test_logout_revokes_session_and_clears_cookie(client, db_session, clock):
    # Arrange: Create User and Active Session in DB
    user = User(email="logout@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-logout"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    # Generate a valid access token to authenticate logout
    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    # Act: Logout
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Assert: 204 and cookie is cleared (has empty/past expiration value)
    assert response.status_code == 204
    # deleted cookie in FastAPI returns empty string or deleted value in Set-Cookie header
    assert (
        "refresh_token" not in response.cookies
        or response.cookies["refresh_token"] == ""
    )

    # Assert: DB session revoked
    db_session.refresh(user_session)
    assert user_session.revoked_at is not None


def test_logout_is_idempotent(client, db_session, clock):
    # Arrange: Create User and Active Session in DB
    user = User(email="logout-idempotent@example.com", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.flush()

    session_id = uuid.uuid4()
    raw_secret = "secret-logout-idem"
    user_session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + SESSION_TTL,
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(user_session)
    db_session.commit()

    # Access token
    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    # Logout 1st time
    client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
    r1 = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r1.status_code == 204

    # Logout 2nd time (with same token, session already revoked)
    r2 = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r2.status_code == 204


def test_get_current_user_profile(client, db_session, clock):
    # Arrange: Create User
    user = User(
        email="profile@example.com",
        display_name="John Doe",
        preferred_language="en",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    # Generate token
    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    # Act: Get profile
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Assert: 200 and matches user data
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["display_name"] == "John Doe"
    assert data["preferred_language"] == "en"
    assert data["role"] == "USER"
    assert data["status"] == "ACTIVE"


def test_update_current_user_profile(client, db_session, clock):
    # Arrange: Create User
    user = User(
        email="update-profile@example.com",
        display_name=None,
        preferred_language="vi",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    # Act: Update editable profile fields
    response = client.patch(
        "/api/v1/auth/me",
        json={"display_name": "  Nguyễn An  ", "preferred_language": "en"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Assert: 200, response and DB both reflect normalized values
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["display_name"] == "Nguyễn An"
    assert data["preferred_language"] == "en"

    db_session.refresh(user)
    assert user.display_name == "Nguyễn An"
    assert user.preferred_language == "en"


def test_update_current_user_profile_post_alias(client, db_session, clock):
    user = User(
        email="update-profile-post@example.com",
        display_name=None,
        preferred_language="vi",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    response = client.post(
        "/api/v1/auth/me/profile",
        json={"display_name": "Profile Post", "preferred_language": "en"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["display_name"] == "Profile Post"
    assert data["preferred_language"] == "en"


def test_update_profile_can_clear_display_name(client, db_session, clock):
    user = User(
        email="clear-name@example.com",
        display_name="Old Name",
        preferred_language="vi",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    response = client.patch(
        "/api/v1/auth/me",
        json={"display_name": "   "},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["display_name"] is None
    db_session.refresh(user)
    assert user.display_name is None


def test_update_profile_rejects_invalid_language(client, db_session, clock):
    user = User(
        email="invalid-lang@example.com",
        display_name=None,
        preferred_language="vi",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    response = client.patch(
        "/api/v1/auth/me",
        json={"preferred_language": "fr"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_profile_fails_if_unauthorized(client):
    # Act: Call without auth
    response = client.get("/api/v1/auth/me")

    # Assert: 401 UNAUTHORIZED
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_profile_fails_if_user_inactive_or_deleted(client, db_session, clock):
    # Arrange: Create locked user
    user = User(
        email="locked@example.com",
        status=UserStatus.LOCKED,
    )
    db_session.add(user)
    db_session.commit()

    # Generate token
    from src.modules.identity.dependencies import get_magic_link_service

    service = get_magic_link_service(db_session)
    access_token = service.create_access_token(user.id)

    # Act: Get profile
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Assert: 401 UNAUTHORIZED
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_magic_link_verification_and_set_password_flow(client, db_session, clock):
    # Arrange: Create token in DB
    email = "new-user-with-pass@example.com"
    raw_token = "token-pass-12345"
    ml_token = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
    )
    db_session.add(ml_token)
    db_session.commit()

    # Step 1: Verify magic link (no password)
    verify_response = client.post(
        "/api/v1/auth/magic-links/verify",
        json={"token": raw_token},
    )
    assert verify_response.status_code == 200
    access_token = verify_response.json()["data"]["access_token"]

    # Step 2: Set password using the access token
    set_password_response = client.post(
        "/api/v1/auth/set-password",
        json={"password": "secure_password_123"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert set_password_response.status_code == 200
    assert set_password_response.json()["success"] is True

    # Assert: User created with password hash in DB
    db_session.expire_all()
    user = db_session.query(User).filter_by(email=email).first()
    assert user is not None
    assert user.password_hash is not None

    # Check password is valid
    from src.modules.identity.service import verify_password

    assert verify_password("secure_password_123", user.password_hash) is True


def test_set_password_fails_if_unauthorized(client):
    # Act: Call without auth
    response = client.post(
        "/api/v1/auth/set-password",
        json={"password": "secure_password_123"},
    )

    # Assert: 401 UNAUTHORIZED
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_with_password_happy_path(client, db_session, clock):
    # Arrange: Create user with password hash in DB
    from src.modules.identity.service import hash_password

    email = "login-pass@example.com"
    password = "secure_password_123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        created_at=clock(),
        updated_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    # Act: Login with correct password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    # Assert: Status 200, cookie set, access token returned
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "access_token" in data
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["email"] == email

    # Assert: Cookie is set with correct attributes
    assert "refresh_token" in response.cookies
    cookie_val = response.cookies["refresh_token"]
    assert "." in cookie_val

    # Assert: Session created
    session_id_str = cookie_val.split(".")[0]
    session_rec = (
        db_session.query(UserSession).filter_by(id=uuid.UUID(session_id_str)).first()
    )
    assert session_rec is not None
    assert session_rec.user_id == user.id
    assert session_rec.revoked_at is None


def test_login_with_password_incorrect_credentials(client, db_session, clock):
    # Arrange: Create user with password hash in DB
    from src.modules.identity.service import hash_password

    email = "wrong-pass@example.com"
    password = "secure_password_123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
        created_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    # Act: Login with wrong password
    response1 = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong_password_xyz"},
    )
    # Assert: 401 INVALID_CREDENTIALS
    assert response1.status_code == 401
    assert response1.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # Act: Login with wrong email
    response2 = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": password},
    )
    # Assert: 401 INVALID_CREDENTIALS
    assert response2.status_code == 401
    assert response2.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_password_missing_password_hash(client, db_session, clock):
    # Arrange: Create user with NO password hash (magic link only)
    email = "magic-only@example.com"
    user = User(
        email=email,
        password_hash=None,
        status=UserStatus.ACTIVE,
        created_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    # Act: Login via password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "some_password"},
    )

    # Assert: 401 INVALID_CREDENTIALS
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_password_inactive_user(client, db_session, clock):
    # Arrange: Create locked user with password hash
    from src.modules.identity.service import hash_password

    email = "inactive-pass@example.com"
    password = "secure_password_123"
    user = User(
        email=email,
        password_hash=hash_password(password),
        status=UserStatus.LOCKED,
        created_at=clock(),
    )
    db_session.add(user)
    db_session.commit()

    # Act: Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    # Assert: 401 UNAUTHORIZED
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
