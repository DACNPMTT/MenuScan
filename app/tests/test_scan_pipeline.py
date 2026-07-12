"""Integration tests for the scan processing pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from src.modules.menu.repository import MenuRepository
from src.modules.menu_scan.models import (
    OcrResult,
    ScanSession,
    ScanSourceFile,
    ScanStatus,
)
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
from src.modules.menu_scan.pipeline import ScanPipeline, _merge_ocr_documents
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


def _one_page_doc(text: str) -> OcrDocument:
    return OcrDocument(
        provider="fake",
        provider_model="fake-v1",
        source_object_key="k",
        detected_language="vi",
        text=text,
        confidence=0.9,
        pages=[
            OcrPage(
                page_index=0,
                width=800,
                height=600,
                text=text,
                blocks=[
                    OcrBlock(
                        id="b0",
                        text=text,
                        bounding_box=OcrBoundingBox(
                            left=0.0, top=0.0, width=1.0, height=1.0
                        ),
                        lines=[OcrLine(id="l0", text=text, bounding_box=_BBOX)],
                    )
                ],
            )
        ],
        processing_time_ms=50,
    )


class SequencedFakeOcrService:
    """Returns a distinct OcrDocument for each successive process() call."""

    def __init__(self, texts: list[str]) -> None:
        self._docs = [_one_page_doc(text) for text in texts]
        self.call_count = 0

    def process(self, source: OcrSource) -> OcrDocument:
        doc = self._docs[self.call_count]
        self.call_count += 1
        return doc


class FakeMenuParser:
    """Menu parser that returns a fixed draft and records images received."""

    def __init__(self, translation_complete: bool = False) -> None:
        self._translation_complete = translation_complete
        self.received_images: object = "unset"
        self.received_preferences_data: object = "unset"
        self.received_is_group: object = "unset"

    def parse(
        self,
        document: OcrDocument,
        *,
        target_language: str = "en",
        images: object = None,
        preferences_data: object = None,
        is_group: bool = False,
    ) -> ParsedMenuDraft:
        self.received_images = images
        self.received_preferences_data = preferences_data
        self.received_is_group = is_group
        return ParsedMenuDraft(
            parsing_provider="fake",
            title="Test Menu",
            source_language="vi",
            target_language=target_language,
            default_currency="VND",
            confidence=0.9,
            translation_complete=self._translation_complete,
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


class SpyTranslationProvider:
    """Wraps another provider and counts translate_batch calls."""

    def __init__(self, wrapped: object) -> None:
        self._wrapped = wrapped
        self.call_count = 0

    def translate_batch(
        self,
        *,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str | None]:
        self.call_count += 1
        return self._wrapped.translate_batch(
            texts=texts,
            source_language=source_language,
            target_language=target_language,
        )


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
    attach_images: bool = False,
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
        attach_images=attach_images,
    )


def _tiny_png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


# ── Tests ───────────────────────────────────────────────────────────


def test_happy_path_pending_to_completed(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Full pipeline: PENDING → COMPLETED with OCR result, menu, and food items."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    parser = FakeMenuParser()
    pipeline = _build_pipeline(db_session_factory, menu_parser=parser)
    pipeline.process(scan_id)

    assert parser.received_preferences_data is None
    assert parser.received_is_group is False

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

        from src.modules.dining.models import (
            DiningSession,
            DiningSessionMode,
            FoodItemRecommendation,
            FoodItemRecommendationParticipantBreakdown,
        )

        dining_session = (
            session.query(DiningSession)
            .filter(DiningSession.scan_session_id == scan_id)
            .one()
        )
        assert dining_session.mode == DiningSessionMode.PERSONAL
        assert dining_session.menu_id == scan.menu.id
        assert len(dining_session.participants) == 1

        recommendations = (
            session.query(FoodItemRecommendation)
            .filter(FoodItemRecommendation.dining_session_id == dining_session.id)
            .all()
        )
        assert len(recommendations) == 2
        assert all(recommendation.suggested_for for recommendation in recommendations)
        assert all(recommendation.fit_reasons for recommendation in recommendations)
        assert all(recommendation.why_suitable for recommendation in recommendations)

        breakdowns = (
            session.query(FoodItemRecommendationParticipantBreakdown)
            .filter(
                FoodItemRecommendationParticipantBreakdown.food_item_recommendation_id.in_(
                    [recommendation.id for recommendation in recommendations]
                )
            )
            .all()
        )
        assert len(breakdowns) == 2
        assert all(breakdown.fit_reasons for breakdown in breakdowns)


def test_pipeline_forwards_page_images_when_attach_images(
    db_session_factory: sessionmaker[Session],
) -> None:
    """attach_images=True + a real image source → parser receives page image bytes."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    parser = FakeMenuParser()
    pipeline = _build_pipeline(
        db_session_factory,
        storage=FakeObjectStorage({"users/u/scans/s/source": _tiny_png_bytes()}),
        menu_parser=parser,
        attach_images=True,
    )
    pipeline.process(scan_id)

    assert isinstance(parser.received_images, list)
    assert len(parser.received_images) == 1
    assert isinstance(parser.received_images[0], bytes)


def test_pipeline_falls_back_to_text_only_when_image_prep_fails(
    db_session_factory: sessionmaker[Session],
) -> None:
    """attach_images=True but source bytes are not a valid image → text-only, no crash."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    parser = FakeMenuParser()
    pipeline = _build_pipeline(
        db_session_factory,
        storage=FakeObjectStorage({"users/u/scans/s/source": b"not-an-image"}),
        menu_parser=parser,
        attach_images=True,
    )
    pipeline.process(scan_id)

    # Image prep is best-effort: bad bytes → None passed, scan still completes.
    assert parser.received_images is None
    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED


def test_merge_ocr_documents_reindexes_and_concatenates() -> None:
    merged = _merge_ocr_documents(
        [_one_page_doc("Page A"), _one_page_doc("Page B"), _one_page_doc("Page C")]
    )
    assert [p.page_index for p in merged.pages] == [0, 1, 2]
    assert merged.text == "Page A\n\nPage B\n\nPage C"
    assert merged.processing_time_ms == 150
    assert merged.metadata["source_file_count"] == 3
    assert merged.metadata["page_count"] == 3


def test_pipeline_ocr_merges_multiple_source_files(
    db_session_factory: sessionmaker[Session],
) -> None:
    """A scan with several source files → one merged OcrResult + menu."""
    key_a = "users/u/scans/s/source"
    key_b = "users/u/scans/s/source-1"
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id
        session.add_all(
            [
                ScanSourceFile(
                    scan_session_id=scan_id,
                    object_key=key_a,
                    file_name="p1.png",
                    mime_type="image/png",
                    file_size=10,
                    page_count=1,
                    sort_order=0,
                ),
                ScanSourceFile(
                    scan_session_id=scan_id,
                    object_key=key_b,
                    file_name="p2.png",
                    mime_type="image/png",
                    file_size=10,
                    page_count=1,
                    sort_order=1,
                ),
            ]
        )
        session.commit()

    ocr = SequencedFakeOcrService(["Phở bò 60.000đ", "Cà phê 25.000đ"])
    pipeline = _build_pipeline(
        db_session_factory,
        storage=FakeObjectStorage({key_a: b"img-a", key_b: b"img-b"}),
        ocr_service=ocr,
    )
    pipeline.process(scan_id)

    assert ocr.call_count == 2
    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED
        assert scan.ocr_result is not None
        # Both pages' text merged into one OcrResult.
        assert "Phở bò" in scan.ocr_result.raw_text
        assert "Cà phê" in scan.ocr_result.raw_text


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


def test_translate_stage_skipped_when_parser_marks_translation_complete(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Parser already translated (e.g. Gemini) → translation service not called."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    spy = SpyTranslationProvider(FakeTranslationProvider())
    pipeline = _build_pipeline(
        db_session_factory,
        menu_parser=FakeMenuParser(translation_complete=True),
        translation_service=TranslationService(provider=spy),
    )
    pipeline.process(scan_id)

    assert spy.call_count == 0
    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED


def test_translate_stage_runs_when_parser_did_not_translate(
    db_session_factory: sessionmaker[Session],
) -> None:
    """Rule-based/fallback parser (no translation) → translation service still called."""
    with db_session_factory() as session:
        scan = _create_scan_session(session)
        scan_id = scan.id

    spy = SpyTranslationProvider(FakeTranslationProvider())
    pipeline = _build_pipeline(
        db_session_factory,
        menu_parser=FakeMenuParser(translation_complete=False),
        translation_service=TranslationService(provider=spy),
    )
    pipeline.process(scan_id)

    assert spy.call_count == 1
    with db_session_factory() as session:
        scan = session.get(ScanSession, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.COMPLETED


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
