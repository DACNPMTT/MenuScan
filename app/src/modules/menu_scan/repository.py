from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.menu_scan.models import OcrResult, ScanSession


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
