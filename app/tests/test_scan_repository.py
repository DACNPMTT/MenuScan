"""Integration tests for ScanSessionRepository's stale-scan reclaim query."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.modules.menu_scan.models import ScanSession, ScanStatus
from src.modules.menu_scan.repository import ScanSessionRepository


def _create_scan(
    session: Session,
    *,
    status: ScanStatus,
    started_at: datetime | None,
) -> ScanSession:
    scan = ScanSession(
        id=uuid.uuid4(),
        user_id=None,
        source_object_key=f"scans/{uuid.uuid4()}",
        source_file_name="menu.png",
        source_mime_type="image/png",
        source_file_size=1024,
        source_page_count=1,
        target_language="en",
        status=status,
        progress=0,
        started_at=started_at,
    )
    if status == ScanStatus.FAILED:
        scan.error_code = "PREVIOUS_ERROR"
        scan.error_message = "Previous error"
    if status == ScanStatus.COMPLETED:
        scan.completed_at = datetime.now(timezone.utc)
    session.add(scan)
    session.commit()
    return scan


def test_reclaim_stale_processing_scans_fails_only_the_stale_one(
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    repository = ScanSessionRepository()

    stale = _create_scan(
        db_session,
        status=ScanStatus.PROCESSING,
        started_at=now - timedelta(minutes=20),
    )
    recent = _create_scan(
        db_session,
        status=ScanStatus.PROCESSING,
        started_at=now - timedelta(minutes=1),
    )

    reclaimed_ids = repository.reclaim_stale_processing_scans(
        db_session,
        stale_before=now - timedelta(minutes=10),
        error_code="SCAN_STALE_TIMEOUT",
        error_message="Scan timed out.",
    )
    db_session.commit()

    assert reclaimed_ids == [stale.id]

    db_session.expire_all()
    reclaimed = db_session.get(ScanSession, stale.id)
    assert reclaimed is not None
    assert reclaimed.status == ScanStatus.FAILED
    assert reclaimed.stage is None
    assert reclaimed.progress == 0
    assert reclaimed.error_code == "SCAN_STALE_TIMEOUT"
    assert reclaimed.error_message == "Scan timed out."
    assert reclaimed.completed_at is not None

    untouched = db_session.get(ScanSession, recent.id)
    assert untouched is not None
    assert untouched.status == ScanStatus.PROCESSING


def test_reclaim_stale_processing_scans_ignores_non_processing_status(
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    repository = ScanSessionRepository()

    old_pending = _create_scan(
        db_session,
        status=ScanStatus.PENDING,
        started_at=None,
    )
    old_completed = _create_scan(
        db_session,
        status=ScanStatus.COMPLETED,
        started_at=now - timedelta(minutes=20),
    )

    reclaimed_ids = repository.reclaim_stale_processing_scans(
        db_session,
        stale_before=now - timedelta(minutes=10),
        error_code="SCAN_STALE_TIMEOUT",
        error_message="Scan timed out.",
    )
    db_session.commit()

    assert reclaimed_ids == []

    db_session.expire_all()
    assert db_session.get(ScanSession, old_pending.id).status == ScanStatus.PENDING
    assert db_session.get(ScanSession, old_completed.id).status == ScanStatus.COMPLETED
