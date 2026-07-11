"""FastAPI dependency wiring for the dining module."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.dining.repository import DiningSessionRepository
from src.modules.dining.service import DiningSessionService


def get_dining_session_service(
    session: Session = Depends(get_db),
) -> DiningSessionService:
    repository = DiningSessionRepository()
    return DiningSessionService(session=session, repository=repository)
