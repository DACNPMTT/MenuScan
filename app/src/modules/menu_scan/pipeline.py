"""Pipeline orchestrator for scan processing.

Coordinates: Storage → OCR → Parser → Translation → Persist results.
Each stage commits its state transition so GET /scans/{id} reflects real progress.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session, sessionmaker

from src.modules.menu.models import FoodItem, Menu
from src.modules.menu.repository import MenuRepository
from src.modules.menu_scan.adapters.storage import (
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
)
from src.modules.menu_scan.exceptions import (
    OcrEmptyResultError,
    OcrProcessingFailedError,
    OcrProviderUnavailableError,
    OcrTimeoutError,
)
from src.modules.menu_scan.menu_parser import MenuParser
from src.modules.menu_scan.menu_validity import looks_like_menu
from src.modules.menu_scan.models import OcrResult, ScanSession, ScanStatus
from src.modules.menu_scan.output_verifier import verify_draft
from src.modules.menu_scan.ocr.document_preprocessor import DocumentPreprocessor
from src.modules.menu_scan.ocr.service import OcrService, OcrSource
from src.modules.menu_scan.ocr_contract import OcrDocument, ParsedMenuDraft
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.translation_service import TranslationService

logger = logging.getLogger(__name__)

# ── Error code constants ────────────────────────────────────────────

_ERROR_SOURCE_FILE_NOT_FOUND = "SOURCE_FILE_NOT_FOUND"
_ERROR_STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
_ERROR_OCR_TIMEOUT = "OCR_TIMEOUT"
_ERROR_OCR_PROVIDER_UNAVAILABLE = "OCR_PROVIDER_UNAVAILABLE"
_ERROR_OCR_EMPTY_RESULT = "OCR_EMPTY_RESULT"
_ERROR_OCR_PROCESSING_FAILED = "OCR_PROCESSING_FAILED"
_ERROR_INVALID_DOCUMENT = "INVALID_DOCUMENT"
_ERROR_PARSING_FAILED = "PARSING_FAILED"
_ERROR_PROCESSING_FAILED = "PROCESSING_FAILED"

# ── Stage constants ─────────────────────────────────────────────────

STAGE_OCR = "OCR"
STAGE_ANALYZING = "ANALYZING"
STAGE_TRANSLATING = "TRANSLATING"
STAGE_FINALIZING = "FINALIZING"

# Dietary taxonomy — the parser may only emit these; anything else is dropped so
# the stored tags stay matchable against a diner's declared allergies / diet.
_KNOWN_ALLERGENS = frozenset(
    {
        "seafood", "shellfish", "fish", "peanut", "tree_nut",
        "egg", "dairy", "gluten", "soy", "sesame",
    }
)
_KNOWN_DIETARY_TAGS = frozenset(
    {
        "contains_pork", "contains_beef", "contains_seafood",
        "contains_alcohol", "vegetarian", "vegan",
    }
)


@dataclass(frozen=True, slots=True)
class ScanPipeline:
    session_factory: sessionmaker[Session]
    storage: ObjectStorage
    ocr_service: OcrService
    menu_parser: MenuParser
    translation_service: TranslationService
    scan_repository: ScanSessionRepository
    menu_repository: MenuRepository
    # When True, the analyze stage also receives the menu page image(s) so a
    # multimodal parser can read the real layout (ADR 0003). Off for the
    # rule-based/text-only path.
    attach_images: bool = False
    image_max_dimension: int = 1536

    def process(self, scan_id: uuid.UUID) -> None:
        """Run the full scan pipeline for the given scan_id."""
        log = logger.bind(scan_id=str(scan_id)) if hasattr(logger, "bind") else logger

        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            if scan is None:
                log.warning("pipeline_scan_not_found scan_id=%s", scan_id)
                return

            if scan.status == ScanStatus.COMPLETED:
                log.info("pipeline_skip_completed scan_id=%s", scan_id)
                return

            if scan.status not in {ScanStatus.PENDING, ScanStatus.FAILED}:
                log.info(
                    "pipeline_skip_invalid_status scan_id=%s status=%s",
                    scan_id,
                    scan.status,
                )
                return

            # Cleanup existing results for retry idempotency
            if scan.status == ScanStatus.FAILED:
                log.info("pipeline_retry_cleanup scan_id=%s", scan_id)
                self.scan_repository.delete_existing_results(session, scan)
                session.commit()

            # Transition to PROCESSING
            _update_scan(
                scan,
                status=ScanStatus.PROCESSING,
                stage=STAGE_OCR,
                progress=5,
                started_at=datetime.now(timezone.utc),
            )
            session.commit()

        # Run pipeline stages outside the initial session
        try:
            ocr_document, page_images = self._stage_ocr(scan_id)
            draft = self._stage_analyze(scan_id, ocr_document, page_images)
            draft = self._stage_translate(scan_id, draft)
            self._stage_finalize(scan_id, ocr_document, draft)
        except _PipelineError as error:
            self._fail_scan(scan_id, error.code, error.message)
            raise
        except Exception as error:
            self._fail_scan(scan_id, _ERROR_PROCESSING_FAILED, str(error))
            raise

    def _stage_ocr(self, scan_id: uuid.UUID) -> tuple[OcrDocument, list[bytes]]:
        """Read source file, run OCR, and (best-effort) prep page images for the LLM."""
        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            assert scan is not None  # noqa: S101

            # A scan may bundle several source files (multiple photos / a PDF).
            # Read them all in upload order; fall back to the single primary key
            # for legacy scans created before scan_source_files existed.
            source_refs = [
                (sf.object_key, sf.mime_type)
                for sf in scan.source_files
            ] or [(scan.source_object_key, scan.source_mime_type)]

            sources: list[OcrSource] = []
            for object_key, mime_type in source_refs:
                try:
                    stored = self.storage.read_object(object_key)
                except ObjectNotFoundError as error:
                    raise _PipelineError(
                        _ERROR_SOURCE_FILE_NOT_FOUND,
                        "Source file not found in storage.",
                    ) from error
                except ObjectStorageError as error:
                    raise _PipelineError(
                        _ERROR_STORAGE_UNAVAILABLE,
                        "Storage is temporarily unavailable.",
                    ) from error
                sources.append(
                    OcrSource(
                        object_key=object_key,
                        data=stored.data,
                        mime_type=mime_type,
                    )
                )

        # Run OCR on each file (outside DB session — may be slow), then merge.
        try:
            ocr_document = _merge_ocr_documents(
                [self.ocr_service.process(source) for source in sources]
            )
        except OcrTimeoutError as error:
            raise _PipelineError(_ERROR_OCR_TIMEOUT, "OCR timed out.") from error
        except OcrProviderUnavailableError as error:
            raise _PipelineError(
                _ERROR_OCR_PROVIDER_UNAVAILABLE,
                "OCR provider is temporarily unavailable.",
            ) from error
        except OcrEmptyResultError as error:
            raise _PipelineError(
                _ERROR_OCR_EMPTY_RESULT,
                "OCR did not return usable text.",
            ) from error
        except OcrProcessingFailedError as error:
            raise _PipelineError(
                _ERROR_OCR_PROCESSING_FAILED,
                "OCR processing failed.",
            ) from error
        except Exception as error:
            raise _PipelineError(
                _ERROR_OCR_PROCESSING_FAILED,
                "OCR processing failed.",
            ) from error

        # Save OcrResult + update stage
        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            assert scan is not None  # noqa: S101

            ocr_result = OcrResult(
                scan_session_id=scan.id,
                raw_text=ocr_document.text,
                detected_language=ocr_document.detected_language,
                confidence_score=(
                    Decimal(str(ocr_document.confidence))
                    if ocr_document.confidence is not None
                    else None
                ),
                provider=ocr_document.provider,
                provider_metadata=dict(ocr_document.metadata),
                processing_time_ms=ocr_document.processing_time_ms,
            )
            self.scan_repository.save_ocr_result(session, ocr_result)
            _update_scan(scan, stage=STAGE_ANALYZING, progress=30)
            session.commit()

        page_images = self._prepare_llm_images(sources)

        logger.info(
            "pipeline_ocr_complete scan_id=%s source_files=%d llm_images=%d",
            scan_id,
            len(sources),
            len(page_images),
        )
        return ocr_document, page_images

    def _prepare_llm_images(self, sources: list[OcrSource]) -> list[bytes]:
        """Downscale every source into per-page PNGs for a multimodal parser.

        Best-effort: image prep must never fail the scan. A source that fails to
        prepare is skipped; the parser still gets the pages that succeeded (or
        falls back to text-only when none do).
        """
        if not self.attach_images:
            return []
        preprocessor = DocumentPreprocessor(
            max_image_dimension=self.image_max_dimension,
            contrast_factor=1.0,
        )
        images: list[bytes] = []
        for source in sources:
            try:
                prepared = preprocessor.prepare(
                    data=source.data,
                    mime_type=source.mime_type,
                )
                images.extend(page.image_bytes for page in prepared.pages)
            except Exception:
                logger.warning(
                    "pipeline_llm_image_prep_failed object_key=%s — skipping",
                    source.object_key,
                )
        return images

    def _stage_analyze(
        self,
        scan_id: uuid.UUID,
        ocr_document: OcrDocument,
        images: list[bytes],
    ) -> ParsedMenuDraft:
        """Parse OCR document into structured menu draft."""
        # Cheap "is this a menu?" gate before the expensive LLM parse: reject
        # obviously-wrong photos (prose, no menu structure) fast instead of
        # spending an LLM call on them.
        if not looks_like_menu(ocr_document):
            raise _PipelineError(
                _ERROR_INVALID_DOCUMENT,
                "The photo does not look like a menu.",
            )

        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            assert scan is not None  # noqa: S101
            target_language = scan.target_language

        try:
            draft = self.menu_parser.parse(
                ocr_document,
                target_language=target_language,
                images=images or None,
                # Keep extraction focused on finding every printed dish. Dining
                # recommendations are generated after persistence from the full
                # saved item list and the dining profile/session preferences.
                preferences_data=None,
                is_group=False,
            )
        except Exception as error:
            logger.exception("pipeline_parse_error scan_id=%s", scan_id)
            raise _PipelineError(
                _ERROR_PARSING_FAILED,
                "Menu parsing failed.",
            ) from error

        # Drop items the parser hallucinated (no name/price grounding in the OCR
        # text). Diacritic-safe and never empties a non-empty draft.
        draft, dropped = verify_draft(draft, ocr_document)
        if dropped:
            logger.info(
                "pipeline_verify_dropped scan_id=%s dropped=%d kept=%d",
                scan_id,
                dropped,
                len(draft.items),
            )

        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            assert scan is not None  # noqa: S101
            _update_scan(scan, stage=STAGE_TRANSLATING, progress=55)
            session.commit()

        logger.info(
            "pipeline_analyze_complete scan_id=%s items=%d", scan_id, len(draft.items)
        )
        return draft

    def _stage_translate(
        self,
        scan_id: uuid.UUID,
        draft: ParsedMenuDraft,
    ) -> ParsedMenuDraft:
        """Translate menu items. Failure is graceful — original content preserved."""
        if draft.translation_complete:
            logger.info(
                "pipeline_translate_skipped_already_translated scan_id=%s", scan_id
            )
        else:
            try:
                draft = self.translation_service.translate_draft(draft)
            except Exception:
                logger.warning(
                    "pipeline_translation_failed scan_id=%s — continuing with originals",
                    scan_id,
                )

        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            assert scan is not None  # noqa: S101
            _update_scan(scan, stage=STAGE_FINALIZING, progress=80)
            session.commit()

        logger.info("pipeline_translate_complete scan_id=%s", scan_id)
        return draft

    def _stage_finalize(
        self,
        scan_id: uuid.UUID,
        ocr_document: OcrDocument,
        draft: ParsedMenuDraft,
    ) -> None:
        """Persist Menu + FoodItems and mark scan COMPLETED."""
        with self.session_factory() as session:
            scan = self.scan_repository.get_scan_for_processing(
                session,
                scan_id=scan_id,
            )
            assert scan is not None  # noqa: S101

            menu = Menu(
                scan_session_id=scan.id,
                title=draft.title or scan.source_file_name,
                source_language=draft.source_language,
                target_language=draft.target_language,
                default_currency=_safe_currency(draft.default_currency),
            )

            food_items = [
                FoodItem(
                    original_name=item.original_name[:255],
                    translated_name=(
                        item.translated_name[:255] if item.translated_name else None
                    ),
                    original_description=item.original_description,
                    translated_description=item.translated_description,
                    assistant_summary=item.assistant_summary,
                    main_ingredients=_clean_free_text_list(item.main_ingredients),
                    ingredient_tags=_clean_free_text_list(item.ingredient_tags),
                    flavor_tags=_clean_free_text_list(item.flavor_tags),
                    texture_tags=_clean_free_text_list(item.texture_tags),
                    cooking_methods=_clean_free_text_list(item.cooking_methods),
                    spice_level=_safe_level(item.spice_level),
                    sweetness_level=_safe_level(item.sweetness_level),
                    saltiness_level=_safe_level(item.saltiness_level),
                    sourness_level=_safe_level(item.sourness_level),
                    richness_level=_safe_level(item.richness_level),
                    oiliness_level=_safe_level(item.oiliness_level),
                    risk_notes=item.risk_notes,
                    price=_safe_decimal(item.price),
                    currency=_safe_currency(item.currency),
                    category=(item.category[:100] if item.category else None),
                    allergens=_clean_tags(item.allergens, _KNOWN_ALLERGENS),
                    dietary_tags=_clean_tags(item.dietary_tags, _KNOWN_DIETARY_TAGS),
                    confidence_score=(
                        Decimal(str(item.confidence))
                        if item.confidence is not None
                        else None
                    ),
                    sort_order=item.sort_order,
                )
                for item in draft.items
            ]

            self.menu_repository.save_menu_with_items(session, menu, food_items)
            session.flush()

            # Link menu and generate recommendations. A scan may come from a
            # dining session, or it may be a normal personal scan; create an
            # implicit personal session so recommendation tables are populated
            # consistently for both flows.
            from src.modules.dining.models import DiningSession, DiningSessionStatus
            from src.modules.dining.service import DiningSessionService

            dining_session = (
                session.query(DiningSession)
                .filter(DiningSession.scan_session_id == scan.id)
                .first()
            )
            if dining_session is None:
                dining_session = _create_personal_dining_session(session, scan, menu)

            if dining_session is not None:
                dining_session.menu_id = menu.id
                dining_session.status = DiningSessionStatus.COMPLETED
                dining_session.updated_at = datetime.now(timezone.utc)

                dining_service = DiningSessionService(session=session)
                dining_service.generate_recommendations(
                    dining_session=dining_session,
                    menu=menu,
                    food_items=food_items,
                    draft_items=draft.items,
                )

            _update_scan(
                scan,
                status=ScanStatus.COMPLETED,
                stage=None,
                progress=100,
                completed_at=datetime.now(timezone.utc),
            )
            session.commit()

        logger.info(
            "pipeline_complete scan_id=%s menu_items=%d",
            scan_id,
            len(food_items),
        )

    def _fail_scan(
        self,
        scan_id: uuid.UUID,
        error_code: str,
        error_message: str,
    ) -> None:
        """Mark scan as FAILED with error details."""
        try:
            with self.session_factory() as session:
                scan = self.scan_repository.get_scan_for_processing(
                    session,
                    scan_id=scan_id,
                )
                if scan is None:
                    return
                _update_scan(
                    scan,
                    status=ScanStatus.FAILED,
                    stage=None,
                    progress=0,
                    error_code=error_code,
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc),
                )
                session.commit()
        except Exception:
            logger.exception("pipeline_fail_scan_error scan_id=%s", scan_id)


class _PipelineError(Exception):
    """Internal error with a stable error code for the scan record."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _create_personal_dining_session(
    session: object,
    scan: ScanSession,
    menu: Menu,
) -> object:
    from src.modules.dining.models import (
        DiningSession,
        DiningSessionMode,
        DiningSessionParticipant,
        DiningSessionParticipantPreference,
        DiningSessionStatus,
    )
    from src.modules.identity.models import FoodProfile, User

    now = datetime.now(timezone.utc)
    user = session.get(User, scan.user_id) if scan.user_id is not None else None
    profile = None
    if scan.user_id is not None:
        profile = (
            session.query(FoodProfile)
            .filter(
                FoodProfile.user_id == scan.user_id,
                FoodProfile.is_default,
                FoodProfile.deleted_at.is_(None),
            )
            .first()
        )

    dining_session = DiningSession(
        created_by_user_id=scan.user_id,
        scan_session_id=scan.id,
        menu_id=menu.id,
        mode=DiningSessionMode.PERSONAL,
        status=DiningSessionStatus.COMPLETED,
        target_language=scan.target_language,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    participant = DiningSessionParticipant(
        dining_session=dining_session,
        user_id=scan.user_id,
        display_name=(
            (profile.display_name if profile is not None else None)
            or (user.display_name if user is not None else None)
            or "Bạn"
        ),
        preferred_language=(
            (profile.preferred_language if profile is not None else None)
            or (user.preferred_language if user is not None else None)
            or scan.target_language
        ),
        joined_at=now,
    )
    if profile is not None:
        participant.preferences = [
            DiningSessionParticipantPreference(
                code=preference.code,
                category=preference.category,
                preference_type=preference.preference_type,
                intensity=preference.intensity,
                importance=preference.importance,
                note=preference.note,
                created_at=now,
            )
            for preference in profile.preferences
        ]
    dining_session.participants = [participant]
    session.add(dining_session)
    session.flush()
    return dining_session


def _update_scan(
    scan: ScanSession,
    *,
    status: ScanStatus | None = None,
    stage: str | None = ...,  # type: ignore[assignment]
    progress: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Mutate scan fields in-place. Uses sentinel for nullable fields."""
    if status is not None:
        scan.status = status
    if stage is not ...:
        scan.stage = stage
    if progress is not None:
        scan.progress = progress
    if error_code is not None:
        scan.error_code = error_code
    if error_message is not None:
        scan.error_message = error_message
    if started_at is not None:
        scan.started_at = started_at
    if completed_at is not None:
        scan.completed_at = completed_at


def _merge_ocr_documents(documents: list[OcrDocument]) -> OcrDocument:
    """Merge per-file OCR results into one document with re-indexed pages.

    Single-file scans pass straight through. For multiple files we concatenate
    the text, renumber pages sequentially across files, sum processing time, and
    keep the first document's provider/source identity.
    """
    if len(documents) == 1:
        return documents[0]

    pages = []
    for document in documents:
        for page in sorted(document.pages, key=lambda item: item.page_index):
            pages.append(page.model_copy(update={"page_index": len(pages)}))

    text = "\n\n".join(document.text for document in documents if document.text)
    confidences = [d.confidence for d in documents if d.confidence is not None]
    detected = next(
        (d.detected_language for d in documents if d.detected_language), None
    )
    metadata: dict[str, object] = {}
    for document in documents:
        metadata.update(document.metadata)
    metadata["source_file_count"] = len(documents)
    metadata["page_count"] = len(pages)

    return documents[0].model_copy(
        update={
            "text": text,
            "pages": pages,
            "detected_language": detected,
            "confidence": (sum(confidences) / len(confidences)) if confidences else None,
            "processing_time_ms": sum(d.processing_time_ms for d in documents),
            "metadata": metadata,
        }
    )


def _clean_tags(values: list[str], allowed: frozenset[str]) -> list[str]:
    """Keep only known taxonomy codes, lowercased and de-duplicated in order."""
    cleaned: list[str] = []
    for value in values:
        code = value.strip().lower()
        if code in allowed and code not in cleaned:
            cleaned.append(code)
    return cleaned


def _clean_free_text_list(values: list[str], *, limit: int = 12) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = value.strip()
        if text and text not in cleaned:
            cleaned.append(text[:80])
        if len(cleaned) >= limit:
            break
    return cleaned


def _safe_level(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, min(5, int(value)))


def _safe_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _safe_currency(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()[:3]
    return cleaned if cleaned else None
