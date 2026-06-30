"""Integration tests for the scan processing pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from src.modules.menu.repository import MenuRepository
from src.modules.menu_scan.models import OcrResult, ScanSession, ScanStatus
from src.modules.menu_scan.ocr.service import OcrSource
from src.modules.menu_scan.ocr_contract import (
    OcrBlock,
    OcrBoundingBox,
    OcrDocument,
    OcrLine,
    OcrPage,
    ParsedMenuDraft,
    ParsedMenuItemDraft,
)
from src.modules.menu_scan.pipeline import ScanPipeline
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.translation_provider import (
    FakeTranslationProvider,
    TranslationTimeoutError,
)
from src.modules.menu_scan.translation_service import TranslationService


# ── Fakes ───────────────────────────────────────────────────────────


@dataclass
class FakeStoredObject:
    data: bytes
    content_type: str | None = None


class FakeObjectStorage:
    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self._objects = objects or {}

    def save_object(self, *, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = data

    def read_object(self, key: str) -> FakeStoredObject:
        if key not in self._objects:
            from src.modules.menu_scan.adapters.storage import ObjectNotFoundError

            raise ObjectNotFoundError(key)
        return FakeStoredObject(data=self._objects[key], content_type="image/png")

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)

    def create_presigned_get_url(self, key: str) -> str | None:
        return None


_BBOX = OcrBoundingBox(left=0.0, top=0.0, width=1.0, height=0.05)

_FAKE_OCR_DOCUMENT = OcrDocument(
    provider="fake",
    provider_model="fake-v1",
    source_object_key="users/u/scans/s/source",
    detected_language="vi",
    text="MENU\nPhở bò 60.000đ\nBún bò Huế 55.000đ",
    confidence=0.95,
    pages=[
        OcrPage(
            page_index=0,
            width=800,
            height=600,
            text="MENU\nPhở bò 60.000đ\nBún bò Huế 55.000đ",
            blocks=[
                OcrBlock(
                    id="b0",
                    text="MENU\nPhở bò 60.000đ\nBún bò Huế 55.000đ",
                    bounding_box=OcrBoundingBox(
                        left=0.0, top=0.0, width=1.0, height=1.0
                    ),
                    lines=[
                        OcrLine(id="l0", text="MENU", bounding_box=_BBOX),
                        OcrLine(
                            id="l1",
                            text="Phở bò 60.000đ",
                            bounding_box=OcrBoundingBox(
                                left=0.0, top=0.1, width=1.0, height=0.05
                            ),
                        ),
                        OcrLine(
                            id="l2",
                            text="Bún bò Huế 55.000đ",
                            bounding_box=OcrBoundingBox(
                                left=0.0, top=0.2, width=1.0, height=0.05
                            ),
                        ),
                    ],
                )
            ],
        )
    ],
    processing_time_ms=100,
)


class FakeOcrService:
    """Fake OCR service that returns a fixture OcrDocument."""

    def __init__(self, document: OcrDocument = _FAKE_OCR_DOCUMENT) -> None:
        self._document = document
        self.call_count = 0

    def process(self, source: OcrSource) -> OcrDocument:
        self.call_count += 1
        return self._document


class FailingOcrService:
    """OCR service that always raises."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def process(self, source: OcrSource) -> OcrDocument:
        raise self._error


class FakeMenuParser:
    """Menu parser that returns a fixed draft."""

    def parse(
        self,
        document: OcrDocument,
        *,
        target_language: str = "en",
    ) -> ParsedMenuDraft:
        return ParsedMenuDraft(
            parsing_provider="fake",
            title="Test Menu",
            source_language="vi",
            target_language=target_language,
            default_currency="VND",
            confidence=0.9,
            items=[
                ParsedMenuItemDraft(
                    original_name="Phở bò",
                    original_description="Nước dùng đậm đà",
                    price="60000.00",
                    currency="VND",
                    category="Món chính",
                    confidence=0.95,
                    sort_order=0,
                ),
                ParsedMenuItemDraft(
                    original_name="Bún bò Huế",
                    price="55000.00",
                    currency="VND",
                    confidence=0.9,
                    sort_order=1,
                ),
            ],
        )


class FailingTranslationProvider:
    """Translation provider that always raises."""

    def translate_batch(
        self,
        *,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str | None]:
        raise TranslationTimeoutError("Translation timed out")


# ── Helpers ─────────────────────────────────────────────────────────


def _create_scan_session(
    session: Session,
    *,
    status: ScanStatus = ScanStatus.PENDING,
    object_key: str = "users/u/scans/s/source",
) -> ScanSession:
    from src.modules.identity.models import User

    user = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()

    scan_id = uuid.uuid4()
    scan = ScanSession(
        id=scan_id,
        user_id=user.id,
        source_object_key=object_key,
        source_file_name="menu.png",
        source_mime_type="image/png",
        source_file_size=1024,
        source_page_count=1,
        target_language="en",
        status=status,
        progress=0,
        created_at=datetime.now(timezone.utc),
    )
    if status == ScanStatus.FAILED:
        scan.error_code = "PREVIOUS_ERROR"
        scan.error_message = "Previous error"
    if status == ScanStatus.COMPLETED:
        scan.completed_at = datetime.now(timezone.utc)
    session.add(scan)
    session.commit()
    return scan


def _build_pipeline(
    session_factory: sessionmaker[Session],
    *,
    storage: FakeObjectStorage | None = None,
    ocr_service: FakeOcrService | FailingOcrService | None = None,
    menu_parser: FakeMenuParser | None = None,
    translation_service: TranslationService | None = None,
) -> ScanPipeline:
    storage = storage or FakeObjectStorage({"users/u/scans/s/source": b"fake-image"})
    return ScanPipeline(
        session_factory=session_factory,
        storage=storage,
        ocr_service=ocr_service or FakeOcrService(),
        menu_parser=menu_parser or FakeMenuParser(),
        translation_service=translation_service
        or TranslationService(
            provider=FakeTranslationProvider(),
        ),
        scan_repository=ScanSessionRepository(),
        menu_repository=MenuRepository(),
    )


# ── Tests ───────────────────────────────────────────────────────────


def test_happy_path_pending_to_completed(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Full pipeline: PENDING → COMPLETED with OCR result, menu, and food items."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    pipeline = _build_pipeline(db_session_factory)
    pipeline.process(scan_id)

    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED
        assert scan.stage is None
        assert scan.progress == 100
        assert scan.completed_at is not None
        assert scan.started_at is not None

        # OcrResult persisted
        assert scan.ocr_result is not None
        assert scan.ocr_result.provider == "fake"
        assert "Phở bò" in scan.ocr_result.raw_text

        # Menu + FoodItems persisted
        assert scan.menu is not None
        assert scan.menu.title == "Test Menu"
        assert scan.menu.target_language == "en"
        assert scan.menu.default_currency == "VND"
        assert len(scan.menu.food_items) == 2

        item_0 = sorted(scan.menu.food_items, key=lambda i: i.sort_order)[0]
        assert item_0.original_name == "Phở bò"
        assert item_0.price == Decimal("60000.00")
        assert item_0.currency == "VND"


def test_ocr_failure_marks_scan_failed(
    db_session_factory: sessionmaker[Session],
) -> None:
    """OCR error → scan FAILED with error code."""
    from src.modules.menu_scan.exceptions import OcrTimeoutError

    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    pipeline = _build_pipeline(
        db_session_factory,
        ocr_service=FailingOcrService(OcrTimeoutError()),
    )

    with pytest.raises(Exception):
        pipeline.process(scan_id)

    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.FAILED
        assert scan.error_code == "OCR_TIMEOUT"


def test_translation_failure_still_completes(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Translation failure is graceful — scan still COMPLETED with original content."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    pipeline = _build_pipeline(
        db_session_factory,
        translation_service=TranslationService(provider=FailingTranslationProvider()),
    )
    pipeline.process(scan_id)

    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED
        assert scan.menu is not None
        assert len(scan.menu.food_items) == 2

        item_0 = sorted(scan.menu.food_items, key=lambda i: i.sort_order)[0]
        assert item_0.original_name == "Phở bò"
        # translated_name may be None since translation failed
        # but original content is preserved


def test_retry_does_not_create_duplicates(
    db_session_factory: sessionmaker[Session],
) -> None:
    """FAILED scan re-processed: old results cleaned up, no duplicates."""
    with db_session_factory() as session:
        scan = _create_scan_session(session, status=ScanStatus.FAILED)
        scan_id = scan.id

        # Simulate existing OcrResult from a previous failed run
        old_ocr = OcrResult(
            scan_session_id=scan_id,
            raw_text="old text",
            provider="old-provider",
        )
        session.add(old_ocr)
        session.commit()

    pipeline = _build_pipeline(db_session_factory)
    pipeline.process(scan_id)

    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED

        # Only one OcrResult (new one, not old)
        assert scan.ocr_result is not None
        assert scan.ocr_result.provider == "fake"
        assert scan.ocr_result.raw_text != "old text"

        # Menu and items exist
        assert scan.menu is not None
        assert len(scan.menu.food_items) == 2


def test_skip_already_completed(db_session_factory: sessionmaker[Session]) -> None:
    """Already completed scan is skipped — no re-processing."""
    with db_session_factory() as session:
        scan = _create_scan_session(session, status=ScanStatus.COMPLETED)
        scan_id = scan.id

    ocr = FakeOcrService()
    pipeline = _build_pipeline(db_session_factory, ocr_service=ocr)
    pipeline.process(scan_id)

    assert ocr.call_count == 0


def test_source_file_not_found_marks_failed(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Missing source file in storage → FAILED with SOURCE_FILE_NOT_FOUND."""
    with db_session_factory() as session:
        scan = _create_scan_session(session, object_key="missing/key")
        scan_id = scan.id

    pipeline = _build_pipeline(
        db_session_factory,
        storage=FakeObjectStorage({}),  # empty storage
    )

    with pytest.raises(Exception):
        pipeline.process(scan_id)

    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.FAILED
        assert scan.error_code == "SOURCE_FILE_NOT_FOUND"
