"""Anti-spam throttle for AI-backed calls (scan, chat).

Not a daily quota — just a minimum gap between two calls per subject (a logged-in
user, or a guest's IP). The check is a single atomic upsert in Postgres,
consistent with the DB-based magic-link cooldown; no Redis needed.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, Request
from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.core.config import settings
from src.core.database import Base, get_db
from src.core.errors import ApplicationError
from src.modules.identity.dependencies import get_optional_current_user
from src.modules.identity.models import User


class AiThrottle(Base):
    """One row per (subject, action) holding the last AI-call timestamp."""

    __tablename__ = "ai_throttle"

    subject_type: Mapped[str] = mapped_column(String(8), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    action: Mapped[str] = mapped_column(String(16), primary_key=True)
    last_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class RateLimitError(ApplicationError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMITED",
            message="You're doing that too fast. Please wait a moment and try again.",
            details={"retry_after": retry_after},
        )


# Conditional atomic upsert: insert the first call, or bump `last_at` only when
# the previous call is older than the gap. If the gap has NOT elapsed, the
# WHERE fails, no row is returned, and the call is rejected — two concurrent
# requests can never both pass.
_UPSERT = text(
    """
    INSERT INTO ai_throttle (subject_type, subject_id, action, last_at)
    VALUES (:subject_type, :subject_id, :action, now())
    ON CONFLICT (subject_type, subject_id, action)
    DO UPDATE SET last_at = now()
    WHERE ai_throttle.last_at < now() - (:gap * interval '1 second')
    RETURNING last_at
    """
)


def throttle(
    session: Session,
    *,
    subject_type: str,
    subject_id: str,
    action: str,
    min_gap_seconds: int,
) -> None:
    """Allow the call only if the last one for this subject+action was more than
    ``min_gap_seconds`` ago; otherwise raise ``RateLimitError`` (429)."""
    row = session.execute(
        _UPSERT,
        {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "action": action,
            "gap": min_gap_seconds,
        },
    ).first()
    if row is None:
        session.rollback()
        raise RateLimitError(retry_after=min_gap_seconds)
    session.commit()


def _client_ip(request: Request) -> str:
    """Real client IP, honoring Cloud Run's ``X-Forwarded-For`` (first hop)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _subject(user: User | None, request: Request) -> tuple[str, str]:
    if user is not None:
        return "user", str(user.id)
    return "ip", _client_ip(request)


def enforce_scan_throttle(
    request: Request,
    session: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
) -> None:
    """FastAPI dependency: throttle the scan endpoint (user by id, guest by IP)."""
    subject_type, subject_id = _subject(user, request)
    throttle(
        session,
        subject_type=subject_type,
        subject_id=subject_id,
        action="scan",
        min_gap_seconds=settings.scan_min_gap_seconds,
    )


# NOTE: the future chat endpoint (module `advisor`) reuses `throttle(...)` with
# action="chat" and `settings.chat_min_gap_seconds`, gated behind
# `get_current_user` (login required).
