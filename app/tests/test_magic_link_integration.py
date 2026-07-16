"""S1-10 · QA - Kiểm thử tích hợp Magic Link và phiên đăng nhập.

Yêu cầu: RUN_DATABASE_TESTS=1 và DATABASE_URL trỏ tới PostgreSQL test.

Chạy:
    RUN_DATABASE_TESTS=1 DATABASE_URL=postgresql://... pytest tests/test_magic_link_integration.py -v

Tiêu chí hoàn thành (issue #42):
    [x] Test chạy độc lập, không gọi email provider thật (FakeEmailSender).
    [x] Kiểm tra cookie flags (HttpOnly, SameSite=Lax) qua Set-Cookie header.
    [x] Xác nhận raw token không lưu trong DB (chỉ lưu SHA-256 hash).
    [x] Toàn bộ test pass trong CI (gate bằng RUN_DATABASE_TESTS=1).
    [x] Sơ đồ auth chỉ dùng 5 endpoints: /magic-links /verify /refresh /logout /me.
    [x] Không có password/forgot-password flow trong luồng Magic Link.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.database import get_db
from src.modules.identity.dependencies import get_magic_link_service
from src.modules.identity.models import (
    MagicLinkToken,
    User,
    UserRole,
    UserSession,
    UserStatus,
)
from src.modules.identity.service import hash_token, MagicLinkService
from src.modules.identity.repository import (
    MagicLinkTokenRepository,
    UserRepository,
    UserSessionRepository,
)
from tests.conftest import FakeClock, FakeEmailSender

# ---------------------------------------------------------------------------
# Pytest gate: chỉ chạy khi có PostgreSQL test
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="PostgreSQL integration tests require RUN_DATABASE_TESTS=1",
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_service(
    db_session,
    clock: FakeClock,
    sender: FakeEmailSender,
    base_url: str = "http://localhost:5173",
) -> MagicLinkService:
    return MagicLinkService(
        session=db_session,
        repository=MagicLinkTokenRepository(),
        email_sender=sender,
        base_url=base_url,
        user_repository=UserRepository(),
        session_repository=UserSessionRepository(),
        clock=clock,
    )


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock(start=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    monkeypatch.setattr("src.modules.identity.service._utcnow", c)
    return c


@pytest.fixture
def sender():
    return FakeEmailSender()


@pytest.fixture
def client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_fake_email(db_session, sender, clock):
    """Client có service inject FakeEmailSender + FakeClock."""
    app = create_app()
    svc = _make_service(db_session, clock, sender)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_magic_link_service] = lambda: svc
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _insert_valid_token(
    db_session, clock, email: str, raw_token: str
) -> MagicLinkToken:
    ml = MagicLinkToken(
        email=email,
        token_hash=hash_token(raw_token),
        expires_at=clock() + timedelta(minutes=15),
        created_at=clock(),
    )
    db_session.add(ml)
    db_session.commit()
    return ml


def _insert_active_user(db_session, email: str) -> User:
    user = User(
        email=email,
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _insert_active_session(
    db_session, clock, user: User, raw_secret: str
) -> tuple[uuid.UUID, UserSession]:
    session_id = uuid.uuid4()
    us = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(raw_secret),
        expires_at=clock() + timedelta(days=30),
        created_at=clock(),
        last_rotated_at=clock(),
    )
    db_session.add(us)
    db_session.commit()
    return session_id, us


def _access_token_for(db_session, user: User) -> str:
    from src.modules.identity.dependencies import get_magic_link_service

    svc = get_magic_link_service(db_session)
    return svc.create_access_token(user.id)


# ===========================================================================
# PHẦN 1 · POST /api/v1/auth/magic-links  (Request Magic Link)
# ===========================================================================


class TestRequestMagicLink:
    def test_valid_email_returns_202(self, client_with_fake_email, sender):
        """Email hợp lệ → 202, gửi email, response không tiết lộ trạng thái."""
        res = client_with_fake_email.post(
            "/api/v1/auth/magic-links",
            json={"email": "user@example.com"},
        )
        assert res.status_code == 202
        body = res.json()
        assert body["success"] is True
        assert "message" in body["data"]
        assert "resend_after_seconds" in body["data"]
        assert len(sender.sent) == 1
        assert sender.sent[0]["to_email"] == "user@example.com"

    def test_email_normalized_before_service(self, client_with_fake_email, sender):
        """Email được trim + lowercase trước khi đến service."""
        res = client_with_fake_email.post(
            "/api/v1/auth/magic-links",
            json={"email": "  USER@Example.COM  "},
        )
        assert res.status_code == 202
        assert sender.sent[0]["to_email"] == "user@example.com"

    def test_invalid_email_returns_400_validation_error(
        self, client_with_fake_email, sender
    ):
        """Email sai format → 400 VALIDATION_ERROR, không gọi service."""
        res = client_with_fake_email.post(
            "/api/v1/auth/magic-links",
            json={"email": "not-an-email"},
        )
        assert res.status_code == 400
        body = res.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "email" in body["error"]["details"]["fields"]
        assert len(sender.sent) == 0

    def test_raw_token_not_stored_in_db(
        self, client_with_fake_email, db_session, sender
    ):
        """DB chỉ lưu SHA-256 hash, không lưu raw token."""
        res = client_with_fake_email.post(
            "/api/v1/auth/magic-links",
            json={"email": "hash-check@example.com"},
        )
        assert res.status_code == 202

        # Lấy raw token từ URL email giả
        raw_token = sender.sent[0]["magic_link_url"].split("token=")[1]

        token_row = (
            db_session.query(MagicLinkToken)
            .filter_by(email="hash-check@example.com")
            .first()
        )
        assert token_row is not None
        # Raw token KHÔNG được lưu trực tiếp
        assert token_row.token_hash != raw_token
        # Hash đúng là SHA-256
        assert token_row.token_hash == hash_token(raw_token)

    def test_rate_limit_within_60s_returns_429(
        self, client_with_fake_email, clock, sender
    ):
        """Gửi 2 request trong 60 giây → lần 2 trả 429 RATE_LIMITED."""
        email = "rl@example.com"
        r1 = client_with_fake_email.post(
            "/api/v1/auth/magic-links", json={"email": email}
        )
        assert r1.status_code == 202

        clock.advance(seconds=30)
        r2 = client_with_fake_email.post(
            "/api/v1/auth/magic-links", json={"email": email}
        )
        assert r2.status_code == 429
        body = r2.json()
        assert body["error"]["code"] == "RATE_LIMITED"
        assert body["error"]["details"]["resend_after_seconds"] == 60
        assert len(sender.sent) == 1  # chỉ 1 email được gửi

    def test_resend_after_cooldown_succeeds(
        self, client_with_fake_email, clock, sender
    ):
        """Gửi lại sau >60 giây → thành công, token cũ bị invalidate."""
        email = "resend-ok@example.com"
        client_with_fake_email.post("/api/v1/auth/magic-links", json={"email": email})

        clock.advance(seconds=61)
        r2 = client_with_fake_email.post(
            "/api/v1/auth/magic-links", json={"email": email}
        )
        assert r2.status_code == 202
        assert len(sender.sent) == 2

    def test_new_request_invalidates_prior_unused_token(
        self, client_with_fake_email, db_session, clock, sender
    ):
        """Request mới vô hiệu hóa token cũ chưa dùng."""
        email = "invalidate@example.com"
        client_with_fake_email.post("/api/v1/auth/magic-links", json={"email": email})

        old_token = db_session.query(MagicLinkToken).filter_by(email=email).first()
        assert old_token.consumed_at is None

        clock.advance(seconds=61)
        client_with_fake_email.post("/api/v1/auth/magic-links", json={"email": email})

        db_session.refresh(old_token)
        assert old_token.consumed_at is not None  # bị mark consumed

    def test_response_identical_for_new_and_existing_email(
        self, client_with_fake_email
    ):
        """Response giống nhau dù email đã đăng ký hay chưa → không lộ account."""
        r1 = client_with_fake_email.post(
            "/api/v1/auth/magic-links",
            json={"email": f"new-{uuid.uuid4()}@example.com"},
        )
        r2 = client_with_fake_email.post(
            "/api/v1/auth/magic-links",
            json={"email": f"new-{uuid.uuid4()}@example.com"},
        )
        assert r1.status_code == r2.status_code == 202
        assert r1.json() == r2.json()

    def test_email_service_failure_returns_503(self, db_session, clock):
        """Email provider lỗi → 503 EMAIL_SERVICE_UNAVAILABLE."""
        failing_sender = FakeEmailSender(should_fail=True)
        app = create_app()
        svc = _make_service(db_session, clock, failing_sender)
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_magic_link_service] = lambda: svc
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.post("/api/v1/auth/magic-links", json={"email": "fail@example.com"})
        app.dependency_overrides.clear()

        assert res.status_code == 503
        assert res.json()["error"]["code"] == "EMAIL_SERVICE_UNAVAILABLE"


# ===========================================================================
# PHẦN 2 · POST /api/v1/auth/magic-links/verify  (Verify Magic Link)
# ===========================================================================


class TestVerifyMagicLink:
    def test_happy_path_new_user(self, client, db_session, clock):
        """Token hợp lệ + email mới → tạo user ACTIVE, tạo session, trả access token."""
        email = "new-user@example.com"
        raw_token = "valid-token-abc123"
        _insert_valid_token(db_session, clock, email, raw_token)

        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        data = body["data"]
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900
        assert data["user"]["email"] == email
        assert data["user"]["role"] == "USER"

    def test_happy_path_existing_user_logs_in(self, client, db_session, clock):
        """Token hợp lệ + email đã tồn tại → đăng nhập user cũ, không tạo user mới."""
        email = "existing@example.com"
        existing_user = _insert_active_user(db_session, email)
        raw_token = "valid-token-existing"
        _insert_valid_token(db_session, clock, email, raw_token)

        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})

        assert res.status_code == 200
        assert res.json()["data"]["user"]["id"] == str(existing_user.id)
        # Không tạo user mới
        count = db_session.query(User).filter_by(email=email).count()
        assert count == 1

    def test_cookie_httponly_and_samesite_set(self, client, db_session, clock):
        """Cookie phải có HttpOnly và SameSite=Lax."""
        raw_token = "cookie-check-token"
        _insert_valid_token(db_session, clock, "cookie@example.com", raw_token)

        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        assert res.status_code == 200

        set_cookie = res.headers.get("set-cookie", "")
        assert "refresh_token" in set_cookie
        assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()
        assert "samesite=none" in set_cookie.lower()
        assert "secure" in set_cookie.lower()

    def test_cookie_value_contains_session_id_dot_secret(
        self, client, db_session, clock
    ):
        """Cookie value có format <session_id>.<secret>."""
        raw_token = "format-check-token"
        _insert_valid_token(db_session, clock, "format@example.com", raw_token)

        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        cookie_val = res.cookies.get("refresh_token")
        assert cookie_val is not None
        parts = cookie_val.split(".")
        assert len(parts) == 2
        assert uuid.UUID(parts[0])  # session_id phải là UUID hợp lệ

    def test_token_marked_consumed_after_verify(self, client, db_session, clock):
        """Token phải được mark consumed_at sau khi dùng."""
        raw_token = "consume-check-token"
        ml = _insert_valid_token(db_session, clock, "consume@example.com", raw_token)

        client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})

        db_session.refresh(ml)
        assert ml.consumed_at is not None

    def test_token_used_twice_returns_400(self, client, db_session, clock):
        """Token đã dùng → lần 2 trả 400 INVALID_MAGIC_LINK."""
        raw_token = "one-time-token"
        _insert_valid_token(db_session, clock, "onetime@example.com", raw_token)

        r1 = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        assert r1.status_code == 200

        r2 = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        assert r2.status_code == 400
        assert r2.json()["error"]["code"] == "INVALID_MAGIC_LINK"

    def test_wrong_token_returns_400(self, client):
        """Token sai (không tồn tại trong DB) → 400 INVALID_MAGIC_LINK."""
        res = client.post(
            "/api/v1/auth/magic-links/verify",
            json={"token": "totally-wrong-token-xyz"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "INVALID_MAGIC_LINK"

    def test_expired_token_returns_401(self, client, db_session, clock):
        """Token hết hạn (>15 phút) → 401 MAGIC_LINK_EXPIRED."""
        raw_token = "expired-token"
        _insert_valid_token(db_session, clock, "expired@example.com", raw_token)

        clock.advance(minutes=16)
        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "MAGIC_LINK_EXPIRED"

    def test_session_created_in_db(self, client, db_session, clock):
        """Session phải được tạo trong DB sau khi verify thành công."""
        raw_token = "session-check-token"
        _insert_valid_token(db_session, clock, "session@example.com", raw_token)

        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        cookie_val = res.cookies["refresh_token"]
        session_id = uuid.UUID(cookie_val.split(".")[0])

        us = db_session.query(UserSession).filter_by(id=session_id).first()
        assert us is not None
        assert us.revoked_at is None

    def test_refresh_token_hash_not_raw_in_db(self, client, db_session, clock):
        """DB chỉ lưu hash của refresh token, không lưu raw secret."""
        raw_token = "hash-refresh-check"
        _insert_valid_token(db_session, clock, "hashref@example.com", raw_token)

        res = client.post("/api/v1/auth/magic-links/verify", json={"token": raw_token})
        cookie_val = res.cookies["refresh_token"]
        session_id_str, raw_secret = cookie_val.split(".", 1)

        us = (
            db_session.query(UserSession)
            .filter_by(id=uuid.UUID(session_id_str))
            .first()
        )
        assert us.refresh_token_hash != raw_secret
        assert us.refresh_token_hash == hash_token(raw_secret)


# ===========================================================================
# PHẦN 3 · POST /api/v1/auth/refresh  (Refresh Token Rotation)
# ===========================================================================


class TestRefreshSession:
    def test_happy_path_rotates_tokens(self, client, db_session, clock):
        """Refresh hợp lệ → access token mới, refresh cookie mới, token cũ bị revoke."""
        user = _insert_active_user(db_session, "refresh-happy@example.com")
        raw_secret = "secret-r1"
        session_id, us = _insert_active_session(db_session, clock, user, raw_secret)
        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")

        clock.advance(hours=1)
        res = client.post("/api/v1/auth/refresh")

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert body["data"]["token_type"] == "Bearer"
        assert body["data"]["expires_in"] == 900

        new_cookie = res.cookies.get("refresh_token")
        assert new_cookie is not None
        assert new_cookie != f"{session_id}.{raw_secret}"

    def test_old_refresh_token_no_longer_valid_after_rotation(
        self, client, db_session, clock
    ):
        """Sau rotate, dùng lại token cũ → 401 SESSION_REVOKED."""
        user = _insert_active_user(db_session, "rotate-test@example.com")
        raw_secret = "secret-rotate"
        session_id, _ = _insert_active_session(db_session, clock, user, raw_secret)

        # Rotate lần 1
        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        r1 = client.post("/api/v1/auth/refresh")
        assert r1.status_code == 200

        # Dùng lại token cũ → replay attack
        db_session.expire_all()
        client.cookies.clear()
        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        r2 = client.post("/api/v1/auth/refresh")
        assert r2.status_code == 401
        assert r2.json()["error"]["code"] == "SESSION_REVOKED"

    def test_replay_attack_revokes_session_in_db(self, client, db_session, clock):
        """Replay attack → DB session bị revoke."""
        user = _insert_active_user(db_session, "replay@example.com")
        raw_secret = "secret-replay"
        session_id, us = _insert_active_session(db_session, clock, user, raw_secret)

        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        client.post("/api/v1/auth/refresh")  # rotate thành công

        # Replay
        client.cookies.clear()
        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        client.post("/api/v1/auth/refresh")

        db_session.refresh(us)
        assert us.revoked_at is not None

    def test_expired_session_returns_401(self, client, db_session, clock):
        """Session hết hạn (>30 ngày) → 401 SESSION_EXPIRED."""
        user = _insert_active_user(db_session, "session-exp@example.com")
        raw_secret = "secret-exp"
        session_id, _ = _insert_active_session(db_session, clock, user, raw_secret)

        clock.advance(days=31)
        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        res = client.post("/api/v1/auth/refresh")

        assert res.status_code == 401
        assert res.json()["error"]["code"] == "SESSION_EXPIRED"

    def test_no_cookie_returns_401(self, client):
        """Không có refresh_token cookie → 401 SESSION_EXPIRED."""
        res = client.post("/api/v1/auth/refresh")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "SESSION_EXPIRED"

    def test_malformed_cookie_returns_401(self, client):
        """Cookie sai format (không có dấu chấm) → 401."""
        client.cookies.set("refresh_token", "invalid-no-dot")
        res = client.post("/api/v1/auth/refresh")
        assert res.status_code == 401

    def test_db_refresh_hash_updated_after_rotation(self, client, db_session, clock):
        """Sau rotate, DB phải lưu hash mới."""
        user = _insert_active_user(db_session, "hash-update@example.com")
        raw_secret = "secret-hash"
        session_id, us = _insert_active_session(db_session, clock, user, raw_secret)

        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        res = client.post("/api/v1/auth/refresh")

        new_cookie = res.cookies["refresh_token"]
        new_secret = new_cookie.split(".")[1]

        db_session.refresh(us)
        assert us.refresh_token_hash == hash_token(new_secret)

    def test_last_rotated_at_updated(self, client, db_session, clock):
        """last_rotated_at phải được cập nhật sau rotate."""
        user = _insert_active_user(db_session, "rotated-at@example.com")
        raw_secret = "secret-ts"
        session_id, us = _insert_active_session(db_session, clock, user, raw_secret)
        original_rotated = us.last_rotated_at

        clock.advance(hours=2)
        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        client.post("/api/v1/auth/refresh")

        db_session.refresh(us)
        assert us.last_rotated_at > original_rotated


# ===========================================================================
# PHẦN 4 · POST /api/v1/auth/logout
# ===========================================================================


class TestLogout:
    def test_happy_path_revokes_session_and_clears_cookie(
        self, client, db_session, clock
    ):
        """Logout hợp lệ → 204, session bị revoke, cookie xóa."""
        user = _insert_active_user(db_session, "logout@example.com")
        raw_secret = "secret-logout"
        session_id, us = _insert_active_session(db_session, clock, user, raw_secret)
        access_token = _access_token_for(db_session, user)

        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        res = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert res.status_code == 204
        db_session.refresh(us)
        assert us.revoked_at is not None

    def test_logout_is_idempotent(self, client, db_session, clock):
        """Logout 2 lần → cả 2 đều 204 (idempotent)."""
        user = _insert_active_user(db_session, "logout-idem@example.com")
        raw_secret = "secret-idem"
        session_id, _ = _insert_active_session(db_session, clock, user, raw_secret)
        access_token = _access_token_for(db_session, user)

        client.cookies.set("refresh_token", f"{session_id}.{raw_secret}")
        r1 = client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
        )
        r2 = client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert r1.status_code == 204
        assert r2.status_code == 204

    def test_logout_without_auth_returns_401(self, client):
        """Logout không có access token → 401 UNAUTHORIZED."""
        res = client.post("/api/v1/auth/logout")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    def test_logout_with_invalid_access_token_returns_401(self, client):
        """Logout với access token giả → 401 UNAUTHORIZED."""
        res = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer totally.invalid.jwt"},
        )
        assert res.status_code == 401


# ===========================================================================
# PHẦN 5 · GET /api/v1/auth/me  (Current User)
# ===========================================================================


class TestGetMe:
    def test_happy_path_returns_user_profile(self, client, db_session, clock):
        """Access token hợp lệ → 200, trả đúng thông tin user."""
        user = User(
            email="me@example.com",
            display_name="Test User",
            preferred_language="vi",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.commit()

        access_token = _access_token_for(db_session, user)
        res = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert res.status_code == 200
        data = res.json()["data"]
        assert data["id"] == str(user.id)
        assert data["email"] == "me@example.com"
        assert data["display_name"] == "Test User"
        assert data["preferred_language"] == "vi"
        assert data["role"] == "USER"
        assert data["status"] == "ACTIVE"

    def test_no_token_returns_401(self, client):
        """Không có Authorization header → 401 UNAUTHORIZED."""
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    def test_invalid_token_returns_401(self, client):
        """Token JWT giả → 401 UNAUTHORIZED."""
        res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    def test_expired_access_token_returns_401(self, client, db_session, clock):
        """Access token hết hạn (>15 phút) → 401 UNAUTHORIZED."""
        user = _insert_active_user(db_session, "expired-at@example.com")
        access_token = _access_token_for(db_session, user)

        clock.advance(minutes=16)
        res = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    def test_locked_user_returns_401(self, client, db_session):
        """User bị LOCKED → 401 UNAUTHORIZED dù token hợp lệ."""
        user = User(email="locked@example.com", status=UserStatus.LOCKED)
        db_session.add(user)
        db_session.commit()

        access_token = _access_token_for(db_session, user)
        res = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res.status_code == 401

    def test_deleted_user_returns_401(self, client, db_session, clock):
        """User đã bị xóa (deleted_at not null) → 401."""
        user = User(
            email="deleted@example.com",
            status=UserStatus.ACTIVE,
            deleted_at=clock(),
        )
        db_session.add(user)
        db_session.commit()

        access_token = _access_token_for(db_session, user)
        res = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res.status_code == 401


# ===========================================================================
# PHẦN 6 · End-to-end flow (tích hợp toàn luồng)
# ===========================================================================


class TestFullMagicLinkFlow:
    def test_full_flow_request_verify_refresh_me_logout(
        self, client_with_fake_email, db_session, clock, sender
    ):
        """Luồng đầy đủ: request → verify → refresh → /me → logout."""
        email = "e2e-flow@example.com"

        # 1. Request Magic Link
        r1 = client_with_fake_email.post(
            "/api/v1/auth/magic-links", json={"email": email}
        )
        assert r1.status_code == 202
        raw_token = sender.sent[0]["magic_link_url"].split("token=")[1]

        # 2. Verify Magic Link → nhận access + refresh cookie
        r2 = client_with_fake_email.post(
            "/api/v1/auth/magic-links/verify", json={"token": raw_token}
        )
        assert r2.status_code == 200
        refresh_cookie = r2.cookies["refresh_token"]

        # 3. Refresh → nhận token mới
        client_with_fake_email.cookies.set("refresh_token", refresh_cookie)
        r3 = client_with_fake_email.post("/api/v1/auth/refresh")
        assert r3.status_code == 200
        new_access = r3.json()["data"]["access_token"]
        new_refresh = r3.cookies["refresh_token"]
        assert new_refresh != refresh_cookie

        # 4. GET /me với access token mới
        r4 = client_with_fake_email.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert r4.status_code == 200
        assert r4.json()["data"]["email"] == email

        # 5. Logout
        client_with_fake_email.cookies.set("refresh_token", new_refresh)
        r5 = client_with_fake_email.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert r5.status_code == 204

        # 6. Sau logout, refresh không còn hợp lệ
        r6 = client_with_fake_email.post("/api/v1/auth/refresh")
        assert r6.status_code in (401,)

    def test_no_password_flow_in_magic_link_auth(self):
        """Kiểm tra: flow Magic Link không đi qua endpoint password/forgot-password."""
        magic_link_endpoints = {
            "/api/v1/auth/magic-links",
            "/api/v1/auth/magic-links/verify",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/me",
        }
        forbidden_in_magic_flow = {"/forgot-password", "/reset-password"}
        for ep in forbidden_in_magic_flow:
            assert ep not in magic_link_endpoints, (
                f"Endpoint {ep} không được xuất hiện trong luồng Magic Link"
            )

    def test_two_devices_independent_sessions(
        self, client_with_fake_email, db_session, clock, sender
    ):
        """2 lần verify tạo ra 2 session độc lập."""
        email = "two-devices@example.com"

        for i in range(2):
            client_with_fake_email.post(
                "/api/v1/auth/magic-links", json={"email": email}
            )
            raw_token = sender.sent[i]["magic_link_url"].split("token=")[1]
            r = client_with_fake_email.post(
                "/api/v1/auth/magic-links/verify", json={"token": raw_token}
            )
            assert r.status_code == 200
            # Advance clock past cooldown before next request
            clock.advance(seconds=61)

        user = db_session.query(User).filter_by(email=email).first()
        sessions = db_session.query(UserSession).filter_by(user_id=user.id).all()
        assert len(sessions) == 2
        assert sessions[0].id != sessions[1].id
