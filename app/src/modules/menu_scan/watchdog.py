"""Reclaims scans stuck in PROCESSING (e.g. worker crash mid-pipeline).

No scheduler/task-queue exists in this codebase (see ADR discussion) — this
is a lightweight in-process asyncio loop started from the app lifespan.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, sessionmaker

from src.modules.menu_scan.repository import ScanSessionRepository

logger = logging.getLogger(__name__)

ERROR_SCAN_STALE_TIMEOUT = "SCAN_STALE_TIMEOUT"
_STALE_ERROR_MESSAGE = (
    "Scan did not complete within the expected processing window and was "
    "automatically marked as failed. Please try scanning again."
)


async def run_stale_scan_watchdog(
    *,
    session_factory: sessionmaker[Session],
    repository: ScanSessionRepository,
    stale_timeout_minutes: int,
    poll_interval_seconds: float = 60.0,
) -> None:
    """Periodically reclaim scans stuck in PROCESSING past the stale timeout.

    Sleeps before the first check (not after) so short-lived processes —
    notably the test suite, which spins up `create_app()` under
    `TestClient` and tears it down well within a minute — never trigger a
    real DB query.
    """
    while True:
        await asyncio.sleep(poll_interval_seconds)
        try:
            await asyncio.to_thread(
                _reclaim_once,
                session_factory,
                repository,
                stale_timeout_minutes,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("scan_watchdog_iteration_failed")


def _reclaim_once(
    session_factory: sessionmaker[Session],
    repository: ScanSessionRepository,
    stale_timeout_minutes: int,
) -> None:
    threshold = datetime.now(timezone.utc) - timedelta(minutes=stale_timeout_minutes)
    with session_factory() as session:
        reclaimed_ids = repository.reclaim_stale_processing_scans(
            session,
            stale_before=threshold,
            error_code=ERROR_SCAN_STALE_TIMEOUT,
            error_message=_STALE_ERROR_MESSAGE,
        )
        session.commit()

    if reclaimed_ids:
        logger.warning(
            "scan_watchdog_reclaimed count=%d scan_ids=%s",
            len(reclaimed_ids),
            reclaimed_ids,
        )
