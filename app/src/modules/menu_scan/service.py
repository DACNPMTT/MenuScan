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
    ScanNotFoundError,
    SourceFileNotFoundError,
    StorageUnavailableError,
    UnsupportedFileTypeError,
)
from src.modules.menu_scan.models import ScanSession, ScanStatus
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.schemas import (
    ScanCreatedData,
    ScanSourceData,
    ScanStatusData,
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 5
SUPPORTED_TARGET_LANGUAGES = {"vi", "en"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
_PDF_PAGE_PATTERN = re.compile(rb"/Type\s*/Page(?!s)\b")
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")


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
        user: User,
        file_name: str | None,
        content: bytes,
        target_language: str | None,
    ) -> ScanCreatedData:
        language = _resolve_target_language(user, target_language)
        source_file = _validate_source_file(
            file_name=file_name,
            content=content,
        )
        scan_id = uuid.uuid4()
        object_key = build_source_object_key(user_id=user.id, scan_id=scan_id)

        self._save_object(
            key=object_key,
            data=source_file.data,
            content_type=source_file.mime_type,
        )
        try:
            scan = ScanSession(
                id=scan_id,
                user_id=user.id,
                source_object_key=object_key,
                source_file_name=source_file.file_name,
                source_mime_type=source_file.mime_type,
                source_file_size=source_file.file_size,
                source_page_count=_page_count(source_file),
                target_language=language,
                status=ScanStatus.PENDING,
                progress=0,
                created_at=datetime.now(timezone.utc),
            )
            self._repository.add(self._session, scan)
            self._session.commit()
        except Exception:
            self._session.rollback()
            self._cleanup_orphan(object_key)
            raise

        return _scan_created_data(scan)

    def get_scan(self, *, user: User, scan_id: uuid.UUID) -> ScanStatusData:
        scan = self._get_owned_scan(user=user, scan_id=scan_id)
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
        user: User,
        scan_id: uuid.UUID,
    ) -> SourceAccess:
        scan = self._get_owned_scan(user=user, scan_id=scan_id)
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

    def _get_owned_scan(self, *, user: User, scan_id: uuid.UUID) -> ScanSession:
        scan = self._repository.get_owned_scan(
            self._session,
            scan_id=scan_id,
            user_id=user.id,
        )
        if scan is None:
            raise ScanNotFoundError()
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


def build_source_object_key(*, user_id: uuid.UUID, scan_id: uuid.UUID) -> str:
    return f"users/{user_id}/scans/{scan_id}/source"


def _resolve_target_language(user: User, target_language: str | None) -> str:
    language = (target_language or user.preferred_language or "vi").strip().lower()
    if language not in SUPPORTED_TARGET_LANGUAGES:
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
