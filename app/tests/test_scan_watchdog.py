"""Unit tests for the stale-scan watchdog loop (no real DB, no async plugin —
just plain `asyncio.run` since this project has no pytest-asyncio/anyio-pytest
setup)."""

from __future__ import annotations

import asyncio

from src.modules.menu_scan.watchdog import run_stale_scan_watchdog


class _FakeSession:
    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def commit(self) -> None:
        pass


class _SpyRepository:
    def __init__(self, target: int = 0) -> None:
        self.call_count = 0
        self._target = target
        self.reached: asyncio.Event | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

    def reclaim_stale_processing_scans(self, session: object, **kwargs: object) -> list:
        # Runs inside asyncio.to_thread (worker thread) — signal the loop safely.
        self.call_count += 1
        if (
            self.reached is not None
            and self.loop is not None
            and self.call_count >= self._target
        ):
            self.loop.call_soon_threadsafe(self.reached.set)
        return []


def test_watchdog_calls_repository_once_per_iteration() -> None:
    async def scenario() -> int:
        repository = _SpyRepository(target=3)
        repository.reached = asyncio.Event()
        repository.loop = asyncio.get_running_loop()
        task = asyncio.create_task(
            run_stale_scan_watchdog(
                session_factory=_FakeSession,
                repository=repository,  # type: ignore[arg-type]
                stale_timeout_minutes=10,
                poll_interval_seconds=0,
            )
        )
        # Deterministic wait: the repository sets the event once called 3×
        # (bounded timeout guards against a hang if the loop never runs).
        await asyncio.wait_for(repository.reached.wait(), timeout=5)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return repository.call_count

    call_count = asyncio.run(scenario())
    assert call_count >= 3


def test_watchdog_cancellation_stops_the_loop_cleanly() -> None:
    async def scenario() -> bool:
        repository = _SpyRepository()
        task = asyncio.create_task(
            run_stale_scan_watchdog(
                session_factory=_FakeSession,
                repository=repository,  # type: ignore[arg-type]
                stale_timeout_minutes=10,
                poll_interval_seconds=60,
            )
        )
        await asyncio.sleep(0)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return task.cancelled()

    assert asyncio.run(scenario()) is True
