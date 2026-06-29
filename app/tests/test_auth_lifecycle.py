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
from src.modules.identity.service import hash_token
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
        expires_at=clock() + timedelta(days=30),
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
        expires_at=clock() + timedelta(days=30),
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
        expires_at=clock() + timedelta(days=30),
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
        expires_at=clock() + timedelta(days=30),
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
        expires_at=clock() + timedelta(days=30),
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
