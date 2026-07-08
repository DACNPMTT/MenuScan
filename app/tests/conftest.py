"""Shared pytest fixtures.

DB-backed fixtures are gated by ``RUN_DATABASE_TESTS=1`` (same convention as
``tests/test_database_integration.py``). HTTP-contract tests never touch the DB.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Importing the model modules registers every table on ``Base.metadata`` so
# ``create_all`` covers the whole schema, not just identity.
from src.core.database import Base
from src.modules.identity.adapters.email import EmailDeliveryError
from src.modules.menu import models as _menu_models  # noqa: F401
from src.modules.menu_scan import models as _menu_scan_models  # noqa: F401
from src.modules.identity import models as _identity_models  # noqa: F401
from src.modules.billing import models as _billing_models  # noqa: F401



# --- Database fixtures --------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    if os.getenv("RUN_DATABASE_TESTS") != "1":
        pytest.skip("PostgreSQL integration tests require RUN_DATABASE_TESTS=1")
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, pool_pre_ping=True)
    # Idempotent: no-op when the migration already created the tables. We do NOT
    # drop on teardown so a shared/migrated dev schema is left intact; per-test
    # isolation comes from the savepoint rollback in ``db_session``.
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Per-test session isolated by savepoint rollback.

    The session joins the outer connection transaction via savepoints, so the
    service's real ``commit()`` releases only a savepoint; rolling back the outer
    transaction on teardown undoes every change.
    """
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def db_session_factory(db_engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Session factory for pipeline tests that manage their own sessions.

    Uses a real transaction per session — each test gets a clean slate via
    table truncation rather than savepoint rollback.
    """
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    yield factory
    # Cleanup: truncate pipeline-related tables after each test. Billing tables
    # reference menus (fk_bills_menu_id_menus), so clear children first to avoid
    # a FK violation on DELETE FROM menus when bill rows exist.
    with factory() as session:
        session.execute(text("DELETE FROM bill_adjustments"))
        session.execute(text("DELETE FROM bill_items"))
        session.execute(text("DELETE FROM bills"))
        session.execute(text("DELETE FROM food_items"))
        session.execute(text("DELETE FROM menus"))
        session.execute(text("DELETE FROM ocr_results"))
        session.execute(text("DELETE FROM scan_sessions"))
        session.execute(text("DELETE FROM user_sessions"))
        session.execute(text("DELETE FROM magic_link_tokens"))
        session.execute(text("DELETE FROM users"))
        session.commit()


# --- Test doubles -------------------------------------------------------------


class FakeClock:
    """Callable clock returning a fixed, advanceable UTC datetime."""

    def __init__(self, start: datetime | None = None) -> None:
        self.current = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current = self.current + timedelta(**kwargs)


class FakeEmailSender:
    """Records every ``send_magic_link`` call; optionally fails."""

    def __init__(self, *, should_fail: bool = False) -> None:
        self.sent: list[dict[str, str]] = []
        self.should_fail = should_fail

    def send_magic_link(self, *, to_email: str, magic_link_url: str) -> None:
        if self.should_fail:
            raise EmailDeliveryError("fake delivery failure")
        self.sent.append({"to_email": to_email, "magic_link_url": magic_link_url})
