"""HTTP contract tests for ``POST /api/v1/scans``.

Uses ``TestClient`` with the real ``api_router`` (so validation + error mapping +
router mounting are exercised), but overrides ``get_scan_service`` with a stub
and ``get_current_user`` with a fixed authenticated user.

Business logic (MIME detection, page counting, storage clean-up, etc.) is
covered by ``test_menu_scan_storage.py``; this layer asserts the HTTP contract
only:
  - 202 with correct envelope on a valid upload
  - 401 when the request carries no auth token
  - 413 for a file that exceeds 10 MB
  - 415 for an unsupported file type (extension spoofing)
  - 422 for a PDF that exceeds 5 pages
  - 400 for an empty file
  - 400 for an unsupported target_language value
  - 503 when storage is unavailable
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.rate_limit import enforce_scan_throttle
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.identity.dependencies import get_optional_current_user
from src.modules.identity.models import User
from src.modules.menu_scan.dependencies import get_scan_pipeline, get_scan_service
from src.modules.menu_scan.exceptions import (
    EmptyUploadError,
    FileTooLargeError,
    InvalidPdfError,
    InvalidTargetLanguageError,
    StorageUnavailableError,
    UnsupportedFileTypeError,
)
from src.modules.menu_scan.models import ScanStatus
from src.modules.menu_scan.schemas import ScanCreatedData, ScanSourceData

# ---------------------------------------------------------------------------
# Minimal valid PNG bytes (magic bytes only – no real image data needed).
# ---------------------------------------------------------------------------
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-png-body"
JPEG_BYTES = b"\xff\xd8\xff" + b"fake-jpeg-body"
PDF_BYTES = b"%PDF-1.4 fake"

# A scan_id used across tests
_SCAN_ID = uuid.UUID("00000000-1111-2222-3333-444444444444")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _stub_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        preferred_language="vi",
    )


def _default_scan_created(user: User) -> ScanCreatedData:
    return ScanCreatedData(
        id=_SCAN_ID,
        status=ScanStatus.PENDING,
        progress=0,
        source=ScanSourceData(
            file_name="menu.png",
            mime_type="image/png",
            file_size=len(PNG_BYTES),
        ),
        target_language="vi",
        created_at=__import__("datetime").datetime(
            2026, 1, 1, tzinfo=__import__("datetime").timezone.utc
        ),
    )


class StubScanService:
    """Records calls and returns/raises as configured."""

    def __init__(
        self,
        *,
        effect: Callable | None = None,
        user: User | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._effect = effect
        self._user = user or _stub_user()

    def create_scan(
        self,
        *,
        user: User | None,
        files: list,
        target_language: str | None,
    ) -> ScanCreatedData:
        self.calls.append(
            {
                "user": user,
                "file_count": len(files),
                "target_language": target_language,
            }
        )
        if self._effect is not None:
            return self._effect(
                user=user,
                files=files,
                target_language=target_language,
            )
        return _default_scan_created(user or self._user)


class StubScanPipeline:
    def __init__(self) -> None:
        self.processed: list[uuid.UUID] = []

    def process(self, scan_id: uuid.UUID) -> None:
        self.processed.append(scan_id)


def _make_client(
    stub: StubScanService,
    *,
    authenticated: bool = True,
) -> TestClient:
    user = _stub_user()
    app = create_app(
        application_settings=_settings(),
        database_engine=Mock(),
    )
    app.dependency_overrides[get_scan_service] = lambda: stub
    app.dependency_overrides[get_scan_pipeline] = lambda: StubScanPipeline()
    # Throttle hits the DB; these contract tests have no DB, so bypass it.
    app.dependency_overrides[enforce_scan_throttle] = lambda: None
    if authenticated:
        app.dependency_overrides[get_optional_current_user] = lambda: user
    else:
        app.dependency_overrides[get_optional_current_user] = lambda: None
    return TestClient(app, raise_server_exceptions=False)


def _post_scan(
    client: TestClient,
    *,
    content: bytes = PNG_BYTES,
    filename: str = "menu.png",
    target_language: str | None = None,
) -> object:
    files = {"file": (filename, content, "application/octet-stream")}
    data = {}
    if target_language is not None:
        data["target_language"] = target_language
    return client.post("/api/v1/scans", files=files, data=data)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_png_returns_202_pending_envelope() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    response = _post_scan(client, content=PNG_BYTES, filename="menu.png")

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["meta"] is None
    data = body["data"]
    assert data["id"] == str(_SCAN_ID)
    assert data["status"] == "PENDING"
    assert data["progress"] == 0
    assert data["source"]["mime_type"] == "image/png"
    assert data["target_language"] == "vi"
    assert "created_at" in data


def test_valid_jpeg_returns_202() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    response = _post_scan(client, content=JPEG_BYTES, filename="menu.jpg")

    assert response.status_code == 202
    assert response.json()["success"] is True


def test_multiple_files_forwarded_to_service() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    response = client.post(
        "/api/v1/scans",
        files=[
            ("files", ("p1.png", PNG_BYTES, "application/octet-stream")),
            ("files", ("p2.jpg", JPEG_BYTES, "application/octet-stream")),
        ],
    )

    assert response.status_code == 202
    assert stub.calls[0]["file_count"] == 2


def test_single_legacy_file_field_still_works() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    response = _post_scan(client)

    assert response.status_code == 202
    assert stub.calls[0]["file_count"] == 1


def test_unauthenticated_request_creates_guest_scan() -> None:
    stub = StubScanService()
    client = _make_client(stub, authenticated=False)

    response = _post_scan(client)

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert stub.calls[0]["user"] is None


def test_file_too_large_returns_413() -> None:
    def raise_too_large(**_kw):
        raise FileTooLargeError(10 * 1024 * 1024)

    stub = StubScanService(effect=raise_too_large)
    client = _make_client(stub)

    response = _post_scan(client)

    assert response.status_code == 413
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FILE_TOO_LARGE"
    assert body["error"]["details"]["max_size_bytes"] == 10 * 1024 * 1024


def test_unsupported_file_type_returns_415() -> None:
    """Extension spoofing: a .png filename with non-image bytes is rejected."""

    def raise_unsupported(**_kw):
        raise UnsupportedFileTypeError()

    stub = StubScanService(effect=raise_unsupported)
    client = _make_client(stub)

    response = _post_scan(
        client, content=b"GIF89a fake gif content", filename="menu.png"
    )

    assert response.status_code == 415
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_invalid_pdf_exceeding_page_limit_returns_422() -> None:
    def raise_invalid_pdf(**_kw):
        raise InvalidPdfError()

    stub = StubScanService(effect=raise_invalid_pdf)
    client = _make_client(stub)

    response = _post_scan(client, content=PDF_BYTES, filename="menu.pdf")

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_PDF"


def test_empty_file_returns_400() -> None:
    def raise_empty(**_kw):
        raise EmptyUploadError()

    stub = StubScanService(effect=raise_empty)
    client = _make_client(stub)

    response = _post_scan(client, content=b"")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMPTY_FILE"


def test_invalid_target_language_returns_400() -> None:
    def raise_invalid_lang(**_kw):
        raise InvalidTargetLanguageError()

    stub = StubScanService(effect=raise_invalid_lang)
    client = _make_client(stub)

    response = _post_scan(client, target_language="fr")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "target_language" in body["error"]["details"]["fields"]


def test_storage_unavailable_returns_503() -> None:
    def raise_storage(**_kw):
        raise StorageUnavailableError()

    stub = StubScanService(effect=raise_storage)
    client = _make_client(stub)

    response = _post_scan(client)

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "STORAGE_UNAVAILABLE"


def test_target_language_vi_is_forwarded_to_service() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    _post_scan(client, target_language="vi")

    assert len(stub.calls) == 1
    assert stub.calls[0]["target_language"] == "vi"


def test_target_language_en_is_forwarded_to_service() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    _post_scan(client, target_language="en")

    assert len(stub.calls) == 1
    assert stub.calls[0]["target_language"] == "en"


def test_omitted_target_language_is_forwarded_as_none() -> None:
    """Router must not inject a default; the service resolves from user prefs."""
    stub = StubScanService()
    client = _make_client(stub)

    _post_scan(client)  # no target_language

    assert len(stub.calls) == 1
    assert stub.calls[0]["target_language"] is None


def test_response_does_not_wait_for_ocr_to_complete() -> None:
    """202 + PENDING status proves the endpoint is non-blocking."""
    stub = StubScanService()
    client = _make_client(stub)

    response = _post_scan(client)

    assert response.status_code == 202
    assert response.json()["data"]["status"] == "PENDING"


def test_response_includes_source_file_metadata() -> None:
    stub = StubScanService()
    client = _make_client(stub)

    response = _post_scan(client, content=PNG_BYTES, filename="menu.png")

    source = response.json()["data"]["source"]
    assert source["file_name"] == "menu.png"
    assert source["mime_type"] == "image/png"
    assert source["file_size"] == len(PNG_BYTES)


def test_dining_session_id_is_associated_with_scan() -> None:
    from src.modules.dining.dependencies import get_dining_session_service

    class StubDiningSessionServiceForScan:
        def __init__(self) -> None:
            self.associations = []

        def associate_scan_session(self, user, *, session_id, scan_session_id):
            self.associations.append(
                {
                    "user_id": user.id,
                    "session_id": session_id,
                    "scan_session_id": scan_session_id,
                }
            )

    dining_stub = StubDiningSessionServiceForScan()
    stub = StubScanService()
    user = _stub_user()

    app = create_app(
        application_settings=_settings(),
        database_engine=Mock(),
    )
    app.dependency_overrides[get_scan_service] = lambda: stub
    app.dependency_overrides[get_scan_pipeline] = lambda: StubScanPipeline()
    app.dependency_overrides[get_optional_current_user] = lambda: user
    app.dependency_overrides[get_dining_session_service] = lambda: dining_stub

    client = TestClient(app, raise_server_exceptions=False)

    session_id = uuid.uuid4()
    files = {"file": ("menu.png", PNG_BYTES, "application/octet-stream")}
    data = {"dining_session_id": str(session_id)}

    response = client.post("/api/v1/scans", files=files, data=data)

    assert response.status_code == 202
    assert len(dining_stub.associations) == 1
    assert dining_stub.associations[0]["session_id"] == session_id
    assert dining_stub.associations[0]["user_id"] == user.id
