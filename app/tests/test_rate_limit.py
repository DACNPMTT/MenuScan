"""DB-backed tests for the AI-call throttle.

Gated by ``RUN_DATABASE_TESTS=1`` (via the ``db_session`` fixture), same as the
other PostgreSQL integration tests — the throttle SQL is Postgres-specific.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.rate_limit import RateLimitError, throttle


def _scan(session: Session, subject_id: str, gap: int = 10) -> None:
    throttle(
        session,
        subject_type="user",
        subject_id=subject_id,
        action="scan",
        min_gap_seconds=gap,
    )


def test_first_call_is_allowed(db_session: Session) -> None:
    _scan(db_session, "user-1")  # no exception


def test_immediate_second_call_is_blocked(db_session: Session) -> None:
    _scan(db_session, "user-2")
    with pytest.raises(RateLimitError):
        _scan(db_session, "user-2")


def test_different_subjects_do_not_share_a_gap(db_session: Session) -> None:
    _scan(db_session, "user-3a")
    _scan(db_session, "user-3b")  # different subject → allowed


def test_different_actions_do_not_share_a_gap(db_session: Session) -> None:
    throttle(
        db_session,
        subject_type="user",
        subject_id="user-4",
        action="scan",
        min_gap_seconds=10,
    )
    # Same subject, different action → independent gap → allowed.
    throttle(
        db_session,
        subject_type="user",
        subject_id="user-4",
        action="chat",
        min_gap_seconds=10,
    )


def test_call_allowed_once_gap_has_elapsed(db_session: Session) -> None:
    _scan(db_session, "user-5", gap=10)
    # Push the recorded time far enough into the past that the gap has elapsed.
    db_session.execute(
        text(
            "UPDATE ai_throttle SET last_at = now() - interval '30 seconds' "
            "WHERE subject_id = :sid"
        ),
        {"sid": "user-5"},
    )
    db_session.commit()
    _scan(db_session, "user-5", gap=10)  # >10s elapsed → allowed again
