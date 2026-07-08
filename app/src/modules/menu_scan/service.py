from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePath

from sqlalchemy.orm import Session

from src.modules.identity.models import User
from src.modules.menu_scan.adapters.storage import (
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
)
from src.modules.menu_scan.exceptions import (
    EmptyUploadError,
    FileTooLargeError,
    InvalidPdfError,
    InvalidTargetLanguageError,
    ScanForbiddenError,
    ScanNotFoundError,
    ScanNotReadyError,
    SourceFileNotFoundError,
    StorageUnavailableError,
    TooManyPagesError,
    UnsupportedFileTypeError,
)
from src.modules.menu_scan.models import ScanSession, ScanSourceFile, ScanStatus
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.schemas import (
    MenuItemData,
    MenuResultData,
    ScanCreatedData,
    ScanListItemData,
    ScanListMenuData,
    ScanListSourceData,
    ScanResultData,
    ScanResultScanData,
    ScanResultSourceData,
    ScanSourceData,
    ScanStatusData,
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 8
MAX_PAGES_PER_SCAN = 8
# One scan may bundle several files (multiple photos or a multi-page PDF). Cap
# the combined payload so a scan can't hold 8 × 10 MB in memory at once.
MAX_TOTAL_UPLOAD_BYTES = 40 * 1024 * 1024
# The scan target language is open-ended: the LLM can translate to any language,
# so we validate the SHAPE of a lowercase language tag (e.g. "vi", "en", "zh",
# "pt-br") rather than gating on a fixed list. The UI offers a curated set, but
# the API/DB accept any well-formed tag (bounded to the column's 10 chars).
_TARGET_LANGUAGE_RE = re.compile(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*")
_MAX_TARGET_LANGUAGE_LEN = 10
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
_PDF_PAGE_PATTERN = re.compile(rb"/Type\s*/Page(?!s)\b")
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")


@dataclass(frozen=True, slots=True)
class UploadCandidate:
    """A raw uploaded file before validation (as received by the router)."""

    file_name: str | None
    content: bytes


@dataclass(frozen=True, slots=True)
class SourceFile:
    data: bytes
    mime_type: str
    file_name: str
    file_size: int


@dataclass(frozen=True, slots=True)
class SourceAccess:
    mime_type: str
    file_name: str
    data: bytes | None = None
    redirect_url: str | None = None


class ScanService:
    def __init__(
        self,
        *,
        session: Session,
        repository: ScanSessionRepository,
        storage: ObjectStorage,
    ) -> None:
        self._session = session
        self._repository = repository
        self._storage = storage

    def create_scan(
        self,
        *,
        user: User | None,
        files: list[UploadCandidate],
        target_language: str | None,
    ) -> ScanCreatedData:
        language = _resolve_target_language(user, target_language)
        if not files:
            raise EmptyUploadError()

        # Validate each file and compute the combined page/byte budget.
        sources = [
            _validate_source_file(file_name=candidate.file_name, content=candidate.content)
            for candidate in files
        ]
        if sum(source.file_size for source in sources) > MAX_TOTAL_UPLOAD_BYTES:
            raise FileTooLargeError(MAX_TOTAL_UPLOAD_BYTES)
        page_counts = [_page_count(source) for source in sources]
        if sum(page_counts) > MAX_PAGES_PER_SCAN:
            raise TooManyPagesError(MAX_PAGES_PER_SCAN)

        scan_id = uuid.uuid4()
        base_key = build_source_object_key(
            user_id=user.id if user else None,
            scan_id=scan_id,
        )

        saved_keys: list[str] = []
        try:
            for index, source in enumerate(sources):
                # First file keeps the historical key; extras get a suffix. This
                # keeps single-file scans byte-for-byte compatible.
                key = base_key if index == 0 else f"{base_key}-{index}"
                self._save_object(
                    key=key,
                    data=source.data,
                    content_type=source.mime_type,
                )
                saved_keys.append(key)
        except Exception:
            for key in saved_keys:
                self._cleanup_orphan(key)
            raise

        primary = sources[0]
        try:
            scan = ScanSession(
                id=scan_id,
                user_id=user.id if user else None,
                source_object_key=saved_keys[0],
                source_file_name=primary.file_name,
                source_mime_type=primary.mime_type,
                source_file_size=primary.file_size,
                source_page_count=sum(page_counts),
                target_language=language,
                status=ScanStatus.PENDING,
                progress=0,
                created_at=datetime.now(timezone.utc),
            )
            scan.source_files = [
                ScanSourceFile(
                    object_key=saved_keys[index],
                    file_name=source.file_name,
                    mime_type=source.mime_type,
                    file_size=source.file_size,
                    page_count=page_counts[index],
                    sort_order=index,
                )
                for index, source in enumerate(sources)
            ]
            self._repository.add(self._session, scan)
            self._session.commit()
        except Exception:
            self._session.rollback()
            for key in saved_keys:
                self._cleanup_orphan(key)
            raise

        return _scan_created_data(scan)

    def list_scans(
        self,
        *,
        user: User,
        page: int,
        page_size: int,
    ) -> tuple[list[ScanListItemData], int]:
        offset = (page - 1) * page_size
        rows = self._repository.list_for_user(
            self._session,
            user_id=user.id,
            limit=page_size,
            offset=offset,
        )
        total = self._repository.count_for_user(self._session, user_id=user.id)
        items = [
            ScanListItemData(
                id=row.id,
                status=row.status,
                created_at=row.created_at,
                completed_at=row.completed_at,
                source=ScanListSourceData(
                    file_name=row.source_file_name,
                    mime_type=row.source_mime_type,
                    file_size=row.source_file_size,
                    preview_url=f"/api/v1/scans/{row.id}/source",
                ),
                menu=(
                    ScanListMenuData(
                        id=row.menu_id,
                        title=row.menu_title or "",
                        is_saved=bool(row.menu_is_saved),
                        item_count=row.item_count,
                    )
                    if row.menu_id is not None
                    else None
                ),
            )
            for row in rows
        ]
        return items, total

    def get_scan(self, *, user: User | None, scan_id: uuid.UUID) -> ScanStatusData:
        scan = self._get_accessible_scan(user=user, scan_id=scan_id)
        error = None
        if scan.error_code is not None:
            error = {
                "code": scan.error_code,
                "message": scan.error_message,
            }
        return ScanStatusData(
            id=scan.id,
            status=scan.status,
            stage=scan.stage,
            progress=scan.progress,
            error=error,
            created_at=scan.created_at,
            completed_at=scan.completed_at,
        )

    def get_source_access(
        self,
        *,
        user: User | None,
        scan_id: uuid.UUID,
    ) -> SourceAccess:
        scan = self._get_accessible_scan(user=user, scan_id=scan_id)
        try:
            redirect_url = self._storage.create_presigned_get_url(
                scan.source_object_key
            )
            if redirect_url is not None:
                return SourceAccess(
                    mime_type=scan.source_mime_type,
                    file_name=scan.source_file_name,
                    redirect_url=redirect_url,
                )

            stored_object = self._storage.read_object(scan.source_object_key)
        except ObjectNotFoundError as error:
            raise SourceFileNotFoundError() from error
        except ObjectStorageError as error:
            raise StorageUnavailableError() from error

        return SourceAccess(
            data=stored_object.data,
            mime_type=stored_object.content_type or scan.source_mime_type,
            file_name=scan.source_file_name,
        )

    def get_result(
        self,
        *,
        user: User | None,
        scan_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[ScanResultData, int]:
        """Build the completed-scan result: scan metadata + extracted menu.

        Returns 409 SCAN_NOT_READY unless the pipeline reached COMPLETED. The
        menu is None only if persistence was skipped (never happens today —
        the pipeline always creates a Menu, possibly with zero items).
        """
        scan = self._get_accessible_scan(user=user, scan_id=scan_id)
        if scan.status != ScanStatus.COMPLETED:
            raise ScanNotReadyError(scan.status.value)

        detected_language = (
            scan.ocr_result.detected_language if scan.ocr_result else None
        )
        processing_time_ms: int | None = None
        if scan.started_at and scan.completed_at:
            processing_time_ms = int(
                (scan.completed_at - scan.started_at).total_seconds() * 1000
            )

        menu_data: MenuResultData | None = None
        total_items = 0
        if scan.menu is not None:
            sorted_items = sorted(
                scan.menu.food_items,
                key=lambda item: (item.sort_order, str(item.id)),
            )
            total_items = len(sorted_items)
            offset = (page - 1) * page_size
            paged_items = sorted_items[offset : offset + page_size]
            menu_data = MenuResultData(
                id=scan.menu.id,
                title=scan.menu.title,
                default_currency=scan.menu.default_currency,
                is_saved=scan.menu.is_saved,
                items=[
                    MenuItemData.model_validate(item)
                    for item in paged_items
                ],
            )

        return (
            ScanResultData(
                scan=ScanResultScanData(
                    id=scan.id,
                    status=scan.status,
                    source=ScanResultSourceData(
                        file_name=scan.source_file_name,
                        mime_type=scan.source_mime_type,
                        file_size=scan.source_file_size,
                        preview_url=f"/api/v1/scans/{scan.id}/source",
                    ),
                    detected_language=detected_language,
                    target_language=scan.target_language,
                    processing_time_ms=processing_time_ms,
                ),
                menu=menu_data,
            ),
            total_items,
        )

    def _get_accessible_scan(
        self,
        *,
        user: User | None,
        scan_id: uuid.UUID,
    ) -> ScanSession:
        scan = self._repository.get_by_id(
            self._session,
            scan_id=scan_id,
        )
        if scan is None:
            raise ScanNotFoundError()
        if scan.user_id is not None and (user is None or scan.user_id != user.id):
            raise ScanForbiddenError()
        return scan

    def _save_object(self, *, key: str, data: bytes, content_type: str) -> None:
        try:
            self._storage.save_object(
                key=key,
                data=data,
                content_type=content_type,
            )
        except ObjectStorageError as error:
            raise StorageUnavailableError() from error

    def _cleanup_orphan(self, object_key: str) -> None:
        try:
            self._storage.delete_object(object_key)
        except ObjectStorageError:
            logger.warning("scan_source_orphan_cleanup_failed")


def build_source_object_key(
    *,
    user_id: uuid.UUID | None,
    scan_id: uuid.UUID,
) -> str:
    owner_segment = f"users/{user_id}" if user_id is not None else "guests"
    return f"{owner_segment}/scans/{scan_id}/source"


def _resolve_target_language(user: User | None, target_language: str | None) -> str:
    preferred = user.preferred_language if user is not None else None
    language = (target_language or preferred or "vi").strip().lower()
    if (
        len(language) > _MAX_TARGET_LANGUAGE_LEN
        or _TARGET_LANGUAGE_RE.fullmatch(language) is None
    ):
        raise InvalidTargetLanguageError()
    return language


def _validate_source_file(*, file_name: str | None, content: bytes) -> SourceFile:
    file_size = len(content)
    if file_size == 0:
        raise EmptyUploadError()
    if file_size > MAX_UPLOAD_BYTES:
        raise FileTooLargeError(MAX_UPLOAD_BYTES)

    mime_type = _detect_mime_type(content)
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise UnsupportedFileTypeError()

    source = SourceFile(
        data=content,
        mime_type=mime_type,
        file_name=_sanitize_file_name(file_name),
        file_size=file_size,
    )
    if mime_type == "application/pdf" and _page_count(source) > MAX_PDF_PAGES:
        raise InvalidPdfError()
    return source


def _detect_mime_type(content: bytes) -> str:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    raise UnsupportedFileTypeError()


def _sanitize_file_name(file_name: str | None) -> str:
    name = PurePath(file_name or "source").name.strip()
    safe_name = _SAFE_FILENAME_PATTERN.sub("_", name).strip(" .")
    if not safe_name:
        safe_name = "source"
    return safe_name[:255]


def _page_count(source_file: SourceFile) -> int:
    if source_file.mime_type != "application/pdf":
        return 1
    page_count = len(_PDF_PAGE_PATTERN.findall(source_file.data))
    if page_count < 1:
        raise InvalidPdfError()
    return page_count


def _scan_created_data(scan: ScanSession) -> ScanCreatedData:
    return ScanCreatedData(
        id=scan.id,
        status=scan.status,
        progress=scan.progress,
        source=ScanSourceData(
            file_name=scan.source_file_name,
            mime_type=scan.source_mime_type,
            file_size=scan.source_file_size,
        ),
        target_language=scan.target_language,
        created_at=scan.created_at,
    )
