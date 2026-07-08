from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from src.core.config import StorageConfig
from src.modules.identity.models import User
from src.modules.menu_scan.adapters.storage import (
    LocalObjectStorage,
    ObjectStorageError,
    S3ObjectStorage,
)
from src.modules.menu_scan.exceptions import (
    ScanForbiddenError,
    StorageUnavailableError,
    TooManyPagesError,
)
from src.modules.menu_scan.models import ScanSession
from src.modules.menu_scan.service import ScanService, UploadCandidate

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"menu-image-bytes"


class FakeSession:
    def __init__(self, *, should_fail_commit: bool = False) -> None:
        self.committed = False
        self.rolled_back = False
        self.should_fail_commit = should_fail_commit

    def commit(self) -> None:
        if self.should_fail_commit:
            raise RuntimeError("database commit failed")
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeScanRepository:
    def __init__(self) -> None:
        self.scans: dict[uuid.UUID, ScanSession] = {}

    def add(self, session: FakeSession, scan: ScanSession) -> ScanSession:
        self.scans[scan.id] = scan
        return scan

    def get_owned_scan(
        self,
        session: FakeSession,
        *,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ScanSession | None:
        scan = self.scans.get(scan_id)
        if scan is None or scan.user_id != user_id:
            return None
        return scan

    def get_by_id(
        self,
        session: FakeSession,
        *,
        scan_id: uuid.UUID,
    ) -> ScanSession | None:
        return self.scans.get(scan_id)


class FailingStorage:
    def save_object(self, *, key: str, data: bytes, content_type: str) -> None:
        raise ObjectStorageError("write failed")

    def read_object(self, key: str) -> object:
        raise AssertionError("read should not be called")

    def delete_object(self, key: str) -> None:
        raise AssertionError("delete should not be called")

    def create_presigned_get_url(self, key: str) -> str | None:
        return None


class CleanupRecordingStorage(LocalObjectStorage):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.deleted_keys: list[str] = []

    def delete_object(self, key: str) -> None:
        self.deleted_keys.append(key)
        super().delete_object(key)


def test_upload_and_read_back_source_binary(tmp_path: Path) -> None:
    user = _user()
    repository = FakeScanRepository()
    service = ScanService(
        session=FakeSession(),
        repository=repository,
        storage=LocalObjectStorage(tmp_path),
    )

    created = service.create_scan(
        user=user,
        files=[UploadCandidate(file_name="../menu.png", content=PNG_BYTES)],
        target_language="en",
    )
    access = service.get_source_access(user=user, scan_id=created.id)
    scan = repository.scans[created.id]

    assert access.data == PNG_BYTES
    assert access.mime_type == "image/png"
    assert scan.source_object_key == f"users/{user.id}/scans/{created.id}/source"
    assert "menu.png" not in scan.source_object_key
    assert scan.source_file_name == "menu.png"


JPEG_BYTES = b"\xff\xd8\xff" + b"menu-jpeg-bytes"


def test_multiple_images_create_source_files_rows(tmp_path: Path) -> None:
    user = _user()
    repository = FakeScanRepository()
    service = ScanService(
        session=FakeSession(),
        repository=repository,
        storage=LocalObjectStorage(tmp_path),
    )

    created = service.create_scan(
        user=user,
        files=[
            UploadCandidate(file_name="p1.png", content=PNG_BYTES),
            UploadCandidate(file_name="p2.jpg", content=JPEG_BYTES),
        ],
        target_language="en",
    )
    scan = repository.scans[created.id]

    # Primary keeps the historical key; the extra gets a -1 suffix.
    base = f"users/{user.id}/scans/{created.id}/source"
    assert scan.source_object_key == base
    assert scan.source_page_count == 2
    assert [sf.object_key for sf in scan.source_files] == [base, f"{base}-1"]
    assert [sf.sort_order for sf in scan.source_files] == [0, 1]
    # Both files round-trip through storage.
    assert service.get_source_access(user=user, scan_id=created.id).data == PNG_BYTES


def test_too_many_pages_rejected(tmp_path: Path) -> None:
    service = ScanService(
        session=FakeSession(),
        repository=FakeScanRepository(),
        storage=LocalObjectStorage(tmp_path),
    )

    with pytest.raises(TooManyPagesError):
        service.create_scan(
            user=_user(),
            files=[
                UploadCandidate(file_name=f"p{i}.png", content=PNG_BYTES)
                for i in range(9)  # 9 single-page images > 8-page cap
            ],
            target_language="vi",
        )


def test_only_owner_can_get_source_url_or_binary(tmp_path: Path) -> None:
    owner = _user()
    other_user = _user()
    repository = FakeScanRepository()
    service = ScanService(
        session=FakeSession(),
        repository=repository,
        storage=LocalObjectStorage(tmp_path),
    )
    created = service.create_scan(
        user=owner,
        files=[UploadCandidate(file_name="menu.png", content=PNG_BYTES)],
        target_language="vi",
    )

    with pytest.raises(ScanForbiddenError):
        service.get_source_access(user=other_user, scan_id=created.id)


def test_storage_failure_returns_stable_error() -> None:
    service = ScanService(
        session=FakeSession(),
        repository=FakeScanRepository(),
        storage=FailingStorage(),
    )

    with pytest.raises(StorageUnavailableError):
        service.create_scan(
            user=_user(),
            files=[UploadCandidate(file_name="menu.png", content=PNG_BYTES)],
            target_language="vi",
        )


def test_scan_create_failure_cleans_up_orphan_object(tmp_path: Path) -> None:
    user = _user()
    session = FakeSession(should_fail_commit=True)
    repository = FakeScanRepository()
    storage = CleanupRecordingStorage(tmp_path)
    service = ScanService(
        session=session,
        repository=repository,
        storage=storage,
    )

    with pytest.raises(RuntimeError, match="database commit failed"):
        service.create_scan(
            user=user,
            files=[UploadCandidate(file_name="menu.png", content=PNG_BYTES)],
            target_language="vi",
        )

    assert session.rolled_back is True
    assert storage.deleted_keys == [
        next(iter(repository.scans.values())).source_object_key
    ]
    assert list(tmp_path.rglob("source")) == []


def test_s3_adapter_creates_signed_private_source_url() -> None:
    storage = S3ObjectStorage(
        StorageConfig(
            provider="s3",
            local_root="storage/objects",
            bucket_name="menuscan-sources",
            endpoint_url="https://object-storage.example",
            region="us-east-1",
            access_key_id="access-key",
            secret_access_key="secret-key",
            session_token=None,
            signed_url_seconds=300,
        )
    )
    key = f"users/{uuid.uuid4()}/scans/{uuid.uuid4()}/source"

    signed_url = storage.create_presigned_get_url(key)
    parsed = urlparse(signed_url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "object-storage.example"
    assert parsed.path == f"/menuscan-sources/{key}"
    assert query["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert query["X-Amz-Expires"] == ["300"]
    assert "X-Amz-Signature" in query


def _user() -> User:
    return User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4()}@example.com",
        preferred_language="vi",
    )
