"""HTTP contract tests for scan GET endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.core.application import create_app
from src.core.config import EmailConfig, Settings, StorageConfig
from src.modules.identity.dependencies import get_current_user, get_optional_current_user
from src.modules.identity.exceptions import UnauthorizedError
from src.modules.identity.models import User
from src.modules.menu_scan.dependencies import get_scan_service
from src.modules.menu_scan.exceptions import (
    ScanForbiddenError,
    ScanNotFoundError,
    ScanNotReadyError,
    SourceFileNotFoundError,
)
from src.modules.menu_scan.models import ScanStatus
from src.modules.menu_scan.schemas import (
    MenuItemData,
    MenuResultData,
    ScanListItemData,
    ScanListMenuData,
    ScanListSourceData,
    ScanResultData,
    ScanResultScanData,
    ScanResultSourceData,
    ScanStatusData,
)
from src.modules.menu_scan.service import SourceAccess

JPEG_BYTES = b"\xff\xd8\xfffake-jpeg-body"
PDF_BYTES = b"%PDF-1.4 fake"

_SCAN_ID = uuid.UUID("00000000-1111-2222-3333-444444444444")
_MENU_ID = uuid.UUID("00000000-aaaa-bbbb-cccc-111111111111")
_ITEM_ID = uuid.UUID("00000000-aaaa-bbbb-cccc-222222222222")
_CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
_COMPLETED_AT = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)


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


def _scan_status(
    *,
    status: ScanStatus = ScanStatus.PENDING,
    stage: str | None = None,
    progress: int = 0,
    error: dict[str, str | None] | None = None,
    completed_at: datetime | None = None,
) -> ScanStatusData:
    return ScanStatusData(
        id=_SCAN_ID,
        status=status,
        stage=stage,
        progress=progress,
        error=error,
        created_at=_CREATED_AT,
        completed_at=completed_at,
    )


def _source_access(
    *,
    data: bytes = JPEG_BYTES,
    mime_type: str = "image/jpeg",
    file_name: str = "menu.jpg",
    redirect_url: str | None = None,
) -> SourceAccess:
    return SourceAccess(
        data=None if redirect_url is not None else data,
        mime_type=mime_type,
        file_name=file_name,
        redirect_url=redirect_url,
    )


def _scan_result(*, status: ScanStatus = ScanStatus.COMPLETED) -> ScanResultData:
    return ScanResultData(
        scan=ScanResultScanData(
            id=_SCAN_ID,
            status=status,
            source=ScanResultSourceData(
                file_name="menu.jpg",
                mime_type="image/jpeg",
                file_size=len(JPEG_BYTES),
                preview_url=f"/api/v1/scans/{_SCAN_ID}/source",
            ),
            detected_language="vi",
            target_language="en",
            processing_time_ms=1200,
        ),
        menu=MenuResultData(
            id=_MENU_ID,
            title="Lunch Menu",
            default_currency="VND",
            is_saved=False,
            items=[
                MenuItemData(
                    id=_ITEM_ID,
                    original_name="Pho bo",
                    translated_name="Beef noodle soup",
                    original_description="Tai chin",
                    translated_description="Rare and well-done beef",
                    price=Decimal("60000.00"),
                    currency="VND",
                    category="Noodles",
                    confidence_score=Decimal("0.9500"),
                    sort_order=0,
                )
            ],
        ),
    )


def _raise_or_return(value: object) -> object:
    if isinstance(value, Exception):
        raise value
    return value


class StubScanService:
    def __init__(
        self,
        *,
        list_items: list[ScanListItemData] | None = None,
        list_total: int = 0,
        scan: ScanStatusData | Exception | None = None,
        source: SourceAccess | Exception | None = None,
        result: ScanResultData | Exception | None = None,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self._list_items = list_items or []
        self._list_total = list_total
        self._scan = scan
        self._source = source
        self._result = result

    def list_scans(
        self,
        *,
        user: User,
        page: int,
        page_size: int,
    ) -> tuple[list[ScanListItemData], int]:
        self.calls.append(
            {
                "method": "list_scans",
                "user": user,
                "page": page,
                "page_size": page_size,
            }
        )
        return self._list_items, self._list_total

    def get_scan(self, *, user: User | None, scan_id: uuid.UUID) -> ScanStatusData:
        self.calls.append({"method": "get_scan", "user": user, "scan_id": scan_id})
        return _raise_or_return(self._scan or _scan_status())  # type: ignore[return-value]

    def get_source_access(self, *, user: User | None, scan_id: uuid.UUID) -> SourceAccess:
        self.calls.append(
            {"method": "get_source_access", "user": user, "scan_id": scan_id}
        )
        return _raise_or_return(self._source or _source_access())  # type: ignore[return-value]

    def get_result(self, *, user: User | None, scan_id: uuid.UUID) -> ScanResultData:
        self.calls.append({"method": "get_result", "user": user, "scan_id": scan_id})
        return _raise_or_return(self._result or _scan_result())  # type: ignore[return-value]


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
    if authenticated:
        app.dependency_overrides[get_optional_current_user] = lambda: user
        app.dependency_overrides[get_current_user] = lambda: user
    else:
        app.dependency_overrides[get_optional_current_user] = lambda: None
        app.dependency_overrides[get_current_user] = lambda: _raise_unauthorized()
    return TestClient(app, raise_server_exceptions=False)


def _raise_unauthorized() -> None:
    raise UnauthorizedError()


def _scan_list_item(
    *,
    scan_id: uuid.UUID = _SCAN_ID,
    status: ScanStatus = ScanStatus.COMPLETED,
    created_at: datetime = _CREATED_AT,
    completed_at: datetime | None = _COMPLETED_AT,
    menu: ScanListMenuData | None = None,
    with_menu: bool = True,
) -> ScanListItemData:
    return ScanListItemData(
        id=scan_id,
        status=status,
        created_at=created_at,
        completed_at=completed_at,
        source=ScanListSourceData(
            file_name="menu.jpg",
            mime_type="image/jpeg",
            file_size=len(JPEG_BYTES),
            preview_url=f"/api/v1/scans/{scan_id}/source",
        ),
        menu=(
            menu
            if menu is not None
            else ScanListMenuData(
                id=_MENU_ID,
                title="Lunch Menu",
                is_saved=False,
                item_count=1,
            )
        )
        if with_menu
        else None,
    )


def test_list_scans_returns_paginated_history() -> None:
    item = _scan_list_item()
    stub = StubScanService(list_items=[item], list_total=21)
    client = _make_client(stub)

    response = client.get("/api/v1/scans", params={"page": 2, "page_size": 20})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"] == {
        "page": 2,
        "page_size": 20,
        "total": 21,
        "total_pages": 2,
    }
    data = body["data"]
    assert data[0]["id"] == str(_SCAN_ID)
    assert data[0]["source"]["preview_url"] == f"/api/v1/scans/{_SCAN_ID}/source"
    assert data[0]["menu"]["item_count"] == 1
    assert stub.calls[0]["method"] == "list_scans"
    assert stub.calls[0]["page"] == 2
    assert stub.calls[0]["page_size"] == 20


def test_list_scans_empty_returns_empty_data_and_meta() -> None:
    stub = StubScanService(list_items=[], list_total=0)
    client = _make_client(stub)

    response = client.get("/api/v1/scans")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"] == {
        "page": 1,
        "page_size": 20,
        "total": 0,
        "total_pages": 0,
    }


def test_list_scans_includes_in_progress_scan_without_menu() -> None:
    item = _scan_list_item(
        status=ScanStatus.PROCESSING,
        completed_at=None,
        with_menu=False,
    )
    stub = StubScanService(list_items=[item], list_total=1)
    client = _make_client(stub)

    response = client.get("/api/v1/scans")

    assert response.status_code == 200
    data = response.json()["data"][0]
    assert data["status"] == "PROCESSING"
    assert data["completed_at"] is None
    assert data["menu"] is None


def test_list_scans_requires_authentication() -> None:
    stub = StubScanService()
    client = _make_client(stub, authenticated=False)

    response = client.get("/api/v1/scans")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert stub.calls == []


def test_get_scan_pending_returns_200() -> None:
    stub = StubScanService(
        scan=_scan_status(status=ScanStatus.PENDING, progress=0)
    )
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"] is None
    data = body["data"]
    assert data["id"] == str(_SCAN_ID)
    assert data["status"] == "PENDING"
    assert data["progress"] == 0
    assert data["error"] is None


def test_get_scan_processing_returns_200() -> None:
    stub = StubScanService(
        scan=_scan_status(
            status=ScanStatus.PROCESSING,
            stage="ocr",
            progress=45,
        )
    )
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "PROCESSING"
    assert data["stage"] == "ocr"
    assert data["progress"] == 45


def test_get_scan_completed_returns_200() -> None:
    stub = StubScanService(
        scan=_scan_status(
            status=ScanStatus.COMPLETED,
            progress=100,
            completed_at=_COMPLETED_AT,
        )
    )
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["completed_at"] is not None


def test_get_scan_failed_returns_200_with_error() -> None:
    stub = StubScanService(
        scan=_scan_status(
            status=ScanStatus.FAILED,
            progress=20,
            error={"code": "OCR_EMPTY_RESULT", "message": "No usable text."},
            completed_at=_COMPLETED_AT,
        )
    )
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "FAILED"
    assert data["error"]["code"] == "OCR_EMPTY_RESULT"
    assert data["error"]["message"] == "No usable text."


def test_get_scan_not_found_returns_404() -> None:
    stub = StubScanService(scan=ScanNotFoundError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"


def test_get_scan_forbidden_returns_403() -> None:
    stub = StubScanService(scan=ScanForbiddenError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_get_scan_allows_guest_lookup() -> None:
    stub = StubScanService()
    client = _make_client(stub, authenticated=False)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert stub.calls[0]["user"] is None


def test_get_source_inline_returns_correct_content_type() -> None:
    stub = StubScanService(source=_source_access(mime_type="image/jpeg"))
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/source")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEG_BYTES


def test_get_source_pdf_returns_correct_content_type() -> None:
    stub = StubScanService(
        source=_source_access(
            data=PDF_BYTES,
            mime_type="application/pdf",
            file_name="menu.pdf",
        )
    )
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/source")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == PDF_BYTES


def test_get_source_content_disposition_inline() -> None:
    stub = StubScanService(source=_source_access(file_name="menu.jpg"))
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/source")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'inline; filename="menu.jpg"'


def test_get_source_redirect_returns_302() -> None:
    redirect_url = "https://storage.example.com/menu.jpg?signature=test"
    stub = StubScanService(source=_source_access(redirect_url=redirect_url))
    client = _make_client(stub)

    response = client.get(
        f"/api/v1/scans/{_SCAN_ID}/source",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == redirect_url


def test_get_source_not_found_returns_404() -> None:
    stub = StubScanService(source=ScanNotFoundError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/source")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"


def test_get_source_forbidden_returns_403() -> None:
    stub = StubScanService(source=ScanForbiddenError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/source")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_get_source_file_missing_returns_404() -> None:
    stub = StubScanService(source=SourceFileNotFoundError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/source")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SOURCE_FILE_NOT_FOUND"


def test_get_result_completed_returns_full_shape() -> None:
    stub = StubScanService(result=_scan_result())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scan"]["id"] == str(_SCAN_ID)
    assert data["scan"]["status"] == "COMPLETED"
    assert data["scan"]["source"]["file_name"] == "menu.jpg"
    assert data["scan"]["detected_language"] == "vi"
    assert data["scan"]["target_language"] == "en"
    assert data["menu"]["id"] == str(_MENU_ID)
    assert data["menu"]["title"] == "Lunch Menu"
    assert data["menu"]["items"][0]["id"] == str(_ITEM_ID)
    assert data["menu"]["items"][0]["original_name"] == "Pho bo"


def test_get_result_price_as_decimal_string() -> None:
    stub = StubScanService(result=_scan_result())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 200
    item = response.json()["data"]["menu"]["items"][0]
    assert item["price"] == "60000.00"


def test_get_result_preview_url_format() -> None:
    stub = StubScanService(result=_scan_result())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 200
    source = response.json()["data"]["scan"]["source"]
    assert source["preview_url"] == f"/api/v1/scans/{_SCAN_ID}/source"


def test_get_result_pending_returns_409() -> None:
    stub = StubScanService(result=ScanNotReadyError(ScanStatus.PENDING.value))
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_NOT_READY"


def test_get_result_processing_returns_409() -> None:
    stub = StubScanService(result=ScanNotReadyError(ScanStatus.PROCESSING.value))
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_NOT_READY"


def test_get_result_failed_returns_409() -> None:
    stub = StubScanService(result=ScanNotReadyError(ScanStatus.FAILED.value))
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_NOT_READY"


def test_get_result_forbidden_returns_403() -> None:
    stub = StubScanService(result=ScanForbiddenError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_get_result_not_found_returns_404() -> None:
    stub = StubScanService(result=ScanNotFoundError())
    client = _make_client(stub)

    response = client.get(f"/api/v1/scans/{_SCAN_ID}/result")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"
