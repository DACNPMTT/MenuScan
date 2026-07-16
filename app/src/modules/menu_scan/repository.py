from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from src.modules.menu.models import FoodItem, Menu
from src.modules.menu_scan.models import OcrResult, ScanSession, ScanStatus


@dataclass(frozen=True, slots=True)
class ScanHistoryRow:
    id: uuid.UUID
    status: ScanStatus
    source_file_name: str
    source_mime_type: str
    source_file_size: int
    created_at: datetime
    completed_at: datetime | None
    menu_id: uuid.UUID | None
    menu_title: str | None
    menu_is_saved: bool | None
    item_count: int


class ScanSessionRepository:
    def add(self, session: Session, scan: ScanSession) -> ScanSession:
        session.add(scan)
        session.flush()
        return scan

    def get_owned_scan(
        self,
        session: Session,
        *,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ScanSession | None:
        statement = select(ScanSession).where(
            ScanSession.id == scan_id,
            ScanSession.user_id == user_id,
            ScanSession.deleted_at.is_(None),
        )
        return session.scalars(statement).first()

    def get_by_id(
        self,
        session: Session,
        *,
        scan_id: uuid.UUID,
    ) -> ScanSession | None:
        statement = select(ScanSession).where(
            ScanSession.id == scan_id,
            ScanSession.deleted_at.is_(None),
        )
        return session.scalars(statement).first()

    def get_scan_for_processing(
        self,
        session: Session,
        *,
        scan_id: uuid.UUID,
    ) -> ScanSession | None:
        """Get scan by ID without ownership check — for background worker."""
        statement = select(ScanSession).where(
            ScanSession.id == scan_id,
            ScanSession.deleted_at.is_(None),
        )
        return session.scalars(statement).first()

    def list_for_user(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> list[ScanHistoryRow]:
        statement = (
            select(
                ScanSession.id,
                ScanSession.status,
                ScanSession.source_file_name,
                ScanSession.source_mime_type,
                ScanSession.source_file_size,
                ScanSession.created_at,
                ScanSession.completed_at,
                Menu.id.label("menu_id"),
                Menu.title.label("menu_title"),
                Menu.is_saved.label("menu_is_saved"),
                func.count(FoodItem.id).label("item_count"),
            )
            .outerjoin(Menu, Menu.scan_session_id == ScanSession.id)
            .outerjoin(FoodItem, FoodItem.menu_id == Menu.id)
            .where(
                ScanSession.user_id == user_id,
                ScanSession.deleted_at.is_(None),
            )
            .group_by(
                ScanSession.id,
                ScanSession.status,
                ScanSession.source_file_name,
                ScanSession.source_mime_type,
                ScanSession.source_file_size,
                ScanSession.created_at,
                ScanSession.completed_at,
                Menu.id,
                Menu.title,
                Menu.is_saved,
            )
            .order_by(desc(ScanSession.created_at), desc(ScanSession.id))
            .limit(limit)
            .offset(offset)
        )
        return [
            ScanHistoryRow(
                id=row.id,
                status=row.status,
                source_file_name=row.source_file_name,
                source_mime_type=row.source_mime_type,
                source_file_size=row.source_file_size,
                created_at=row.created_at,
                completed_at=row.completed_at,
                menu_id=row.menu_id,
                menu_title=row.menu_title,
                menu_is_saved=row.menu_is_saved,
                item_count=row.item_count,
            )
            for row in session.execute(statement)
        ]

    def count_for_user(self, session: Session, *, user_id: uuid.UUID) -> int:
        statement = (
            select(func.count())
            .select_from(ScanSession)
            .where(
                ScanSession.user_id == user_id,
                ScanSession.deleted_at.is_(None),
            )
        )
        return session.scalar(statement) or 0

    def save_ocr_result(self, session: Session, ocr_result: OcrResult) -> None:
        session.add(ocr_result)
        session.flush()

    def delete_existing_results(self, session: Session, scan: ScanSession) -> None:
        """Delete OcrResult and Menu (CASCADE → FoodItems) for retry idempotency."""
        if scan.menu is not None:
            session.delete(scan.menu)
        if scan.ocr_result is not None:
            session.delete(scan.ocr_result)
        session.flush()

    def reclaim_stale_processing_scans(
        self,
        session: Session,
        *,
        stale_before: datetime,
        error_code: str,
        error_message: str,
    ) -> list[uuid.UUID]:
        """Atomically fail scans stuck in PROCESSING past `stale_before`.

        Single UPDATE...RETURNING — race-safe across concurrent processes/
        replicas without SELECT-then-write or SELECT...FOR UPDATE SKIP LOCKED.
        Caller is responsible for committing.
        """
        statement = (
            update(ScanSession)
            .where(
                ScanSession.status == ScanStatus.PROCESSING,
                ScanSession.started_at.is_not(None),
                ScanSession.started_at < stale_before,
                ScanSession.deleted_at.is_(None),
            )
            .values(
                status=ScanStatus.FAILED,
                stage=None,
                progress=0,
                error_code=error_code,
                error_message=error_message,
                completed_at=func.now(),
            )
            .returning(ScanSession.id)
            .execution_options(synchronize_session=False)
        )
        return [row[0] for row in session.execute(statement)]
