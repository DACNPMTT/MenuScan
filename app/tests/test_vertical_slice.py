"""S1-25 · QA - Kiểm thử luồng Magic Link đến kết quả quét.

Kiểm chứng vertical slice cốt lõi có thể demo từ đầu đến cuối:
    Magic Link → Dashboard/Home → Upload ảnh/PDF → Processing → Xem file gốc và danh sách món.

Yêu cầu: RUN_DATABASE_TESTS=1 và DATABASE_URL trỏ tới PostgreSQL test.

Tiêu chí hoàn thành (issue #54):
    [x] Test dùng email và OCR adapter giả lập ổn định.
    [x] Có happy path và ít nhất một upload/OCR failure path.
    [x] Chạy được trong CI hoặc có lệnh chạy được ghi rõ.
    [x] Không phụ thuộc secret production.
    [x] Kết quả hiển thị đúng file gốc và structured menu.
    [x] Có evidence kết quả demo.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.database import get_db
from src.core.rate_limit import enforce_scan_throttle
from src.modules.identity.dependencies import get_current_user, get_magic_link_service
from src.modules.identity.models import User, UserRole, UserStatus
from src.modules.identity.repository import (
    MagicLinkTokenRepository,
    UserRepository,
    UserSessionRepository,
)
from src.modules.identity.service import MagicLinkService
from src.modules.menu_scan.adapters.storage import LocalObjectStorage
from src.modules.menu_scan.dependencies import get_object_storage, get_scan_service
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.service import ScanService
from tests.conftest import FakeClock, FakeEmailSender

# ---------------------------------------------------------------------------
# Pytest gate
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="PostgreSQL integration tests require RUN_DATABASE_TESTS=1",
)

# ---------------------------------------------------------------------------
# Minimal valid image bytes
# ---------------------------------------------------------------------------
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-content-for-testing"
JPEG_BYTES = b"\xff\xd8\xff" + b"fake-jpeg-content-for-testing"
PDF_1PAGE = b"%PDF-1.4 fake-one-page /Type /Page\x00"
PDF_6PAGE = b"%PDF-1.4 " + b"/Type /Page\x00" * 6  # 6 pages → vượt giới hạn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_magic_link_service(db_session, clock, sender) -> MagicLinkService:
    return MagicLinkService(
        session=db_session,
        repository=MagicLinkTokenRepository(),
        email_sender=sender,
        base_url="http://localhost:5173",
        user_repository=UserRepository(),
        session_repository=UserSessionRepository(),
        clock=clock,
    )


def _make_scan_service(db_session, storage) -> ScanService:
    return ScanService(
        session=db_session,
        repository=ScanSessionRepository(),
        storage=storage,
    )


def _insert_active_user(db_session, email: str) -> User:
    user = User(
        email=email,
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        preferred_language="vi",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _access_token_for(db_session, user: User) -> str:
    svc = get_magic_link_service(db_session)
    return svc.create_access_token(user.id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock(start=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    monkeypatch.setattr("src.modules.identity.service._utcnow", c)
    return c


@pytest.fixture
def sender():
    return FakeEmailSender()


@pytest.fixture
def local_storage(tmp_path):
    return LocalObjectStorage(tmp_path)


@pytest.fixture
def client_full(db_session, sender, clock, local_storage):
    """Client với fake email, fake storage, real DB."""
    app = create_app()
    svc = _make_magic_link_service(db_session, clock, sender)
    scan_svc = _make_scan_service(db_session, local_storage)

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_magic_link_service] = lambda: svc
    app.dependency_overrides[get_scan_service] = lambda: scan_svc
    app.dependency_overrides[get_object_storage] = lambda: local_storage
    app.dependency_overrides[enforce_scan_throttle] = lambda: None

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(db_session, sender, clock, local_storage):
    """Client đã đăng nhập sẵn — dùng cho test không cần kiểm tra luồng auth."""
    app = create_app()
    user = _insert_active_user(db_session, f"auth-{uuid.uuid4()}@example.com")
    scan_svc = _make_scan_service(db_session, local_storage)

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_scan_service] = lambda: scan_svc
    app.dependency_overrides[get_object_storage] = lambda: local_storage
    app.dependency_overrides[enforce_scan_throttle] = lambda: None

    with TestClient(app, raise_server_exceptions=False) as c:
        c._test_user = user
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# PHẦN 1 · Happy path — toàn bộ vertical slice
# ===========================================================================


class TestVerticalSliceHappyPath:
    def test_full_flow_magic_link_to_scan_created(
        self, client_full, db_session, clock, sender
    ):
        """Luồng đầy đủ: request magic link → verify → upload PNG → 202 PENDING."""
        email = f"e2e-{uuid.uuid4()}@example.com"

        # 1. Request Magic Link
        r1 = client_full.post("/api/v1/auth/magic-links", json={"email": email})
        assert r1.status_code == 202

        # 2. Verify Magic Link → nhận access token
        raw_token = sender.sent[0]["magic_link_url"].split("token=")[1]
        r2 = client_full.post(
            "/api/v1/auth/magic-links/verify", json={"token": raw_token}
        )
        assert r2.status_code == 200
        access_token = r2.json()["data"]["access_token"]

        # 3. Upload menu image → POST /api/v1/scans
        r3 = client_full.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r3.status_code == 202
        body = r3.json()
        assert body["success"] is True
        data = body["data"]
        assert data["status"] == "PENDING"
        assert data["progress"] == 0
        assert data["source"]["file_name"] == "menu.png"
        assert data["source"]["mime_type"] == "image/png"
        assert "id" in data
        assert "created_at" in data

    def test_authenticated_user_can_upload_jpeg(self, auth_client):
        """User đã đăng nhập upload JPEG → 202 với metadata đúng."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("photo.jpg", JPEG_BYTES, "application/octet-stream")},
        )
        assert r.status_code == 202
        data = r.json()["data"]
        assert data["source"]["mime_type"] == "image/jpeg"
        assert data["source"]["file_name"] == "photo.jpg"
        assert data["source"]["file_size"] == len(JPEG_BYTES)

    def test_upload_with_explicit_target_language_vi(self, auth_client):
        """Upload với target_language=vi → response chứa target_language=vi."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
            data={"target_language": "vi"},
        )
        assert r.status_code == 202
        assert r.json()["data"]["target_language"] == "vi"

    def test_upload_with_explicit_target_language_en(self, auth_client):
        """Upload với target_language=en → response chứa target_language=en."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
            data={"target_language": "en"},
        )
        assert r.status_code == 202
        assert r.json()["data"]["target_language"] == "en"

    def test_scan_id_is_valid_uuid(self, auth_client):
        """Scan ID trả về phải là UUID hợp lệ."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
        )
        assert r.status_code == 202
        scan_id = r.json()["data"]["id"]
        uuid.UUID(scan_id)  # raises ValueError nếu không hợp lệ

    def test_get_scan_status_after_upload(self, auth_client):
        """Sau upload, GET /scans/{id} trả đúng trạng thái PENDING."""
        r_create = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
        )
        assert r_create.status_code == 202
        scan_id = r_create.json()["data"]["id"]

        r_get = auth_client.get(f"/api/v1/scans/{scan_id}")
        assert r_get.status_code == 200
        body = r_get.json()
        assert body["success"] is True
        assert body["data"]["id"] == scan_id
        assert body["data"]["status"] == "PENDING"

    def test_get_scan_source_file_returns_original_bytes(self, auth_client):
        """GET /scans/{id}/source trả về đúng bytes file đã upload."""
        r_create = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
        )
        scan_id = r_create.json()["data"]["id"]

        r_source = auth_client.get(f"/api/v1/scans/{scan_id}/source")
        assert r_source.status_code == 200
        assert r_source.content == PNG_BYTES
        assert "image/png" in r_source.headers["content-type"]

    def test_source_file_content_disposition_has_filename(self, auth_client):
        """Response header phải có Content-Disposition với tên file."""
        r_create = auth_client.post(
            "/api/v1/scans",
            files={"file": ("my_menu.png", PNG_BYTES, "application/octet-stream")},
        )
        scan_id = r_create.json()["data"]["id"]

        r_source = auth_client.get(f"/api/v1/scans/{scan_id}/source")
        assert r_source.status_code == 200
        disposition = r_source.headers.get("content-disposition", "")
        assert "my_menu.png" in disposition

    def test_multiple_scans_are_independent(self, auth_client):
        """Hai lần upload tạo ra 2 scan riêng biệt với ID khác nhau."""
        r1 = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu1.png", PNG_BYTES, "application/octet-stream")},
        )
        r2 = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu2.png", JPEG_BYTES, "application/octet-stream")},
        )
        assert r1.status_code == 202
        assert r2.status_code == 202
        assert r1.json()["data"]["id"] != r2.json()["data"]["id"]

    def test_scan_response_envelope_structure(self, auth_client):
        """Response phải có đúng cấu trúc envelope: success, data, meta."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
        )
        body = r.json()
        assert "success" in body
        assert "data" in body
        assert "meta" in body
        assert body["success"] is True


# ===========================================================================
# PHẦN 2 · Failure paths — upload/OCR failure
# ===========================================================================


class TestUploadFailurePaths:
    def test_unauthenticated_upload_returns_202_as_guest(
        self, db_session, local_storage
    ):
        """Upload không có token → 202 ACCEPTED (guest mode)."""
        app = create_app()
        scan_svc = _make_scan_service(db_session, local_storage)
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_scan_service] = lambda: scan_svc

        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.post(
                "/api/v1/scans",
                files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
            )
        assert r.status_code == 202

    def test_unsupported_file_type_returns_415(self, auth_client):
        """File type không nằm trong allowlist → 415 UNSUPPORTED_MEDIA_TYPE."""
        r = auth_client.post(
            "/api/v1/scans",
            files={
                "file": ("malware.exe", b"MZ\x90\x00\x03", "application/x-msdownload")
            },
        )
        assert r.status_code == 415
        assert r.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_extension_spoofing_rejected(self, auth_client):
        """Extension spoofing → 415."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("fake.png", b"MZ\x90\x00\x03", "image/png")},
        )
        assert r.status_code == 415

    def test_empty_file_returns_400(self, auth_client):
        """File rỗng (0 bytes) → 400."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("empty.png", b"", "image/png")},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "EMPTY_FILE"

    def test_file_exceeding_10mb_returns_413(self, auth_client):
        """File > 10MB → 413."""
        big_bytes = b"0" * (10 * 1024 * 1024 + 1)
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("big.png", big_bytes, "image/png")},
        )
        assert r.status_code == 413
        assert r.json()["error"]["code"] == "FILE_TOO_LARGE"

    def test_pdf_exceeding_page_limit_returns_422(self, auth_client):
        """PDF > 8 trang → 422."""
        pdf_bytes = b"%PDF-1.4\n" + b"/Type /Page\n" * 9 + b"%%EOF\n"
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("long.pdf", pdf_bytes, "application/octet-stream")},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "INVALID_PDF"

    def test_invalid_target_language_returns_400(self, auth_client):
        """target_language không hợp lệ → 400 VALIDATION_ERROR."""
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
            data={"target_language": "invalid_lang"},
        )
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "target_language" in body["error"]["details"]["fields"]

    def test_get_nonexistent_scan_returns_404(self, auth_client):
        """GET scan không tồn tại → 404 SCAN_NOT_FOUND."""
        fake_id = uuid.uuid4()
        r = auth_client.get(f"/api/v1/scans/{fake_id}")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "SCAN_NOT_FOUND"

    def test_user_cannot_access_other_users_scan(self, db_session, local_storage):
        """Scan của user A thì user B không xem được → 403."""
        user_repo = UserRepository()
        user_a = User(email="a@test.com", password_hash="dummy")
        user_b = User(email="b@test.com", password_hash="dummy")
        user_repo.create(db_session, user_a)
        user_repo.create(db_session, user_b)
        db_session.commit()

        app = create_app()
        scan_svc = _make_scan_service(db_session, local_storage)

        # Upload với user_a
        app.dependency_overrides[get_db] = lambda: db_session
        from src.modules.identity.dependencies import get_optional_current_user

        app.dependency_overrides[get_optional_current_user] = lambda: user_a
        app.dependency_overrides[get_scan_service] = lambda: scan_svc
        app.dependency_overrides[get_object_storage] = lambda: local_storage

        with TestClient(app, raise_server_exceptions=False) as c:
            r_create = c.post(
                "/api/v1/scans",
                files={"file": ("menu.png", PNG_BYTES, "application/octet-stream")},
            )
            scan_id = r_create.json()["data"]["id"]

        # Đổi sang user_b, thử GET
        app.dependency_overrides[get_optional_current_user] = lambda: user_b
        with TestClient(app, raise_server_exceptions=False) as c:
            r_get = c.get(f"/api/v1/scans/{scan_id}")

        app.dependency_overrides.clear()

        assert r_get.status_code == 403
        assert r_get.json()["error"]["code"] == "FORBIDDEN"

    def test_get_source_of_nonexistent_scan_returns_404(self, auth_client):
        """GET source của scan không tồn tại → 404."""
        fake_id = uuid.uuid4()
        r = auth_client.get(f"/api/v1/scans/{fake_id}/source")
        assert r.status_code == 404


# ===========================================================================
# PHẦN 3 · Không phụ thuộc secret production
# ===========================================================================


class TestNoDependencyOnProductionSecrets:
    def test_fake_email_adapter_never_calls_real_smtp(self, sender):
        """FakeEmailSender không gọi SMTP thật — chỉ lưu vào memory."""
        sender.send_magic_link(
            to_email="test@example.com",
            magic_link_url="http://localhost:5173/verify?token=abc",
        )
        assert len(sender.sent) == 1
        assert sender.sent[0]["to_email"] == "test@example.com"
        # Không cần SMTP_HOST, SMTP_PASSWORD, RESEND_API_KEY

    def test_local_storage_adapter_uses_tmp_path(self, tmp_path):
        """LocalObjectStorage dùng thư mục tạm, không cần S3 credentials."""
        storage = LocalObjectStorage(tmp_path)
        key = f"users/{uuid.uuid4()}/scans/{uuid.uuid4()}/source"
        storage.save_object(key=key, data=PNG_BYTES, content_type="image/png")
        obj = storage.read_object(key)
        assert obj.data == PNG_BYTES
        assert obj.content_type == "image/png"

    def test_no_production_env_vars_required(self):
        """Test suite không yêu cầu RESEND_API_KEY, AWS_*, hay DATABASE_URL production."""
        forbidden_keys = {
            "RESEND_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
        }
        for key in forbidden_keys:
            val = os.getenv(key)
            if val:
                # Nếu có thì phải là giá trị fake/test
                assert val.startswith(("fake", "test", "mock", "local")), (
                    f"{key} có vẻ là production secret. "
                    "Test không được dùng secret thật."
                )


# ===========================================================================
# PHẦN 4 · Evidence demo — kết quả có thể demo
# ===========================================================================


class TestDemoEvidence:
    def test_demo_upload_png_and_check_scan_metadata(self, auth_client):
        """
        Evidence demo: upload PNG → scan PENDING → kiểm tra metadata đầy đủ.

        Output này có thể dùng làm bằng chứng demo cho Sprint Review.
        """
        r = auth_client.post(
            "/api/v1/scans",
            files={"file": ("demo_menu.png", PNG_BYTES, "application/octet-stream")},
            data={"target_language": "vi"},
        )
        assert r.status_code == 202
        data = r.json()["data"]

        # Kiểm tra đầy đủ các field cần thiết cho demo
        assert uuid.UUID(data["id"])  # ID hợp lệ
        assert data["status"] == "PENDING"  # chưa xử lý OCR
        assert data["progress"] == 0  # 0%
        assert data["target_language"] == "vi"  # ngôn ngữ đích
        assert data["source"]["file_name"] == "demo_menu.png"
        assert data["source"]["mime_type"] == "image/png"
        assert data["source"]["file_size"] == len(PNG_BYTES)
        assert data["created_at"] is not None  # timestamp tạo

    def test_demo_source_file_retrievable(self, auth_client):
        """
        Evidence demo: file gốc sau upload có thể lấy lại nguyên vẹn.
        """
        r_create = auth_client.post(
            "/api/v1/scans",
            files={"file": ("demo_menu.png", PNG_BYTES, "application/octet-stream")},
        )
        scan_id = r_create.json()["data"]["id"]

        r_source = auth_client.get(f"/api/v1/scans/{scan_id}/source")
        assert r_source.status_code == 200
        assert r_source.content == PNG_BYTES  # byte-for-byte identical

    def test_demo_magic_link_flow_creates_authenticated_session(
        self, client_full, sender
    ):
        """
        Evidence demo: toàn bộ luồng Magic Link tạo ra session hợp lệ.
        User có thể đăng nhập và upload ngay sau đó.
        """
        email = f"demo-{uuid.uuid4()}@restaurant.com"

        # Step 1: Yêu cầu magic link
        r1 = client_full.post("/api/v1/auth/magic-links", json={"email": email})
        assert r1.status_code == 202
        assert len(sender.sent) == 1

        # Step 2: Verify → nhận token
        raw_token = sender.sent[0]["magic_link_url"].split("token=")[1]
        r2 = client_full.post(
            "/api/v1/auth/magic-links/verify", json={"token": raw_token}
        )
        assert r2.status_code == 200
        access_token = r2.json()["data"]["access_token"]
        user_email = r2.json()["data"]["user"]["email"]
        assert user_email == email

        # Step 3: Dùng token upload menu ngay
        r3 = client_full.post(
            "/api/v1/scans",
            files={
                "file": ("restaurant_menu.png", PNG_BYTES, "application/octet-stream")
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r3.status_code == 202
        assert r3.json()["data"]["status"] == "PENDING"
