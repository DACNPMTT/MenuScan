"""Integration tests for ``MagicLinkService`` against a real PostgreSQL.

Gated by ``RUN_DATABASE_TESTS=1`` (same convention as
``test_database_integration.py``). The ``db_session`` fixture isolates each test
via savepoint rollback.
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from src.modules.identity.exceptions import (
    EmailServiceUnavailableError,
    MagicLinkRateLimitedError,
)
from src.modules.identity.models import MagicLinkToken, User
from src.modules.identity.repository import MagicLinkTokenRepository
from src.modules.identity.service import (
    MAGIC_LINK_SUCCESS_MESSAGE,
    MAGIC_LINK_TTL,
    MagicLinkService,
)
from tests.conftest import FakeClock, FakeEmailSender


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="PostgreSQL integration tests require RUN_DATABASE_TESTS=1",
)


def _make_service(
    session,
    clock: FakeClock,
    sender: FakeEmailSender,
    base_url: str = "http://localhost:5173",
) -> MagicLinkService:
    return MagicLinkService(
        session=session,
        repository=MagicLinkTokenRepository(),
        email_sender=sender,
        base_url=base_url,
        clock=clock,
    )


def _tokens_for(session, email: str) -> list[MagicLinkToken]:
    return list(
        session.scalars(
            select(MagicLinkToken).where(MagicLinkToken.email == email)
        )
    )


def test_request_creates_token_with_hash_and_sends_link(db_session):
    clock = FakeClock()
    sender = FakeEmailSender()
    service = _make_service(db_session, clock, sender)

    email = f"user-{uuid.uuid4()}@example.com"
    data = service.request_magic_link(email)

    assert data.message == MAGIC_LINK_SUCCESS_MESSAGE

    tokens = _tokens_for(db_session, email)
    assert len(tokens) == 1
    token = tokens[0]

    # Hash stored, never the raw token.
    assert token.token_hash
    assert token.consumed_at is None
    assert token.user_id is None
    assert len(sender.sent) == 1
    sent = sender.sent[0]
    assert sent["to_email"] == email
    assert "token=" in sent["magic_link_url"]
    raw_token = sent["magic_link_url"].split("token=", 1)[1]
    assert raw_token  # non-empty
    assert token.token_hash != raw_token
    # Raw token must not appear anywhere in the persisted row.
    persisted = "".join(
        str(getattr(token, col)) for col in ("token_hash", "email")
    )
    assert raw_token not in persisted


def test_resend_within_cooldown_raises_rate_limited(db_session):
    clock = FakeClock()
    sender = FakeEmailSender()
    service = _make_service(db_session, clock, sender)

    email = f"rl-{uuid.uuid4()}@example.com"
    service.request_magic_link(email)

    clock.advance(seconds=30)
    with pytest.raises(MagicLinkRateLimitedError) as exc_info:
        service.request_magic_link(email)

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMITED"
    assert exc_info.value.details["resend_after_seconds"] == 60
    # No second token, no second email.
    assert len(_tokens_for(db_session, email)) == 1
    assert len(sender.sent) == 1


def test_resend_after_cooldown_succeeds(db_session):
    clock = FakeClock()
    sender = FakeEmailSender()
    service = _make_service(db_session, clock, sender)

    email = f"ok-{uuid.uuid4()}@example.com"
    service.request_magic_link(email)

    clock.advance(seconds=61)
    service.request_magic_link(email)

    assert len(_tokens_for(db_session, email)) == 2
    assert len(sender.sent) == 2


def test_new_request_invalidates_prior_unused_tokens(db_session):
    clock = FakeClock()
    sender = FakeEmailSender()
    service = _make_service(db_session, clock, sender)

    email = f"inv-{uuid.uuid4()}@example.com"
    service.request_magic_link(email)

    tokens = _tokens_for(db_session, email)
    assert len(tokens) == 1
    t1 = tokens[0]
    assert t1.consumed_at is None

    clock.advance(seconds=61)
    service.request_magic_link(email)

    db_session.refresh(t1)
    assert t1.consumed_at is not None

    tokens = _tokens_for(db_session, email)
    active = [t for t in tokens if t.consumed_at is None]
    assert len(active) == 1


def test_token_expires_at_is_fifteen_minutes(db_session):
    clock = FakeClock()
    sender = FakeEmailSender()
    service = _make_service(db_session, clock, sender)

    email = f"exp-{uuid.uuid4()}@example.com"
    service.request_magic_link(email)

    token = _tokens_for(db_session, email)[0]
    assert token.expires_at - token.created_at == MAGIC_LINK_TTL
    assert MAGIC_LINK_TTL == timedelta(minutes=15)


def test_email_sender_failure_raises_email_unavailable(db_session):
    clock = FakeClock()
    sender = FakeEmailSender(should_fail=True)
    service = _make_service(db_session, clock, sender)

    email = f"fail-{uuid.uuid4()}@example.com"
    with pytest.raises(EmailServiceUnavailableError) as exc_info:
        service.request_magic_link(email)

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "EMAIL_SERVICE_UNAVAILABLE"
    # Token row is still committed even though email delivery failed.
    assert len(_tokens_for(db_session, email)) == 1


def test_response_identical_for_existing_and_new_email(db_session):
    clock = FakeClock()
    sender = FakeEmailSender()
    service = _make_service(db_session, clock, sender)

    registered_email = f"real-{uuid.uuid4()}@example.com"
    db_session.add(User(email=registered_email))
    db_session.flush()

    registered = service.request_magic_link(registered_email)
    # Advance past cooldown so the second request is not rate-limited.
    clock.advance(seconds=61)
    unregistered_email = f"new-{uuid.uuid4()}@example.com"
    unregistered = service.request_magic_link(unregistered_email)

    # Identical response payload -> no enumeration surface.
    assert registered.model_dump() == unregistered.model_dump()
