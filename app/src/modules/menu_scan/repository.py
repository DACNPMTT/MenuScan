from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.menu_scan.models import ScanSession


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
