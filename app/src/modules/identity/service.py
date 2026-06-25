"""Magic-link request workflow.

Synchronous to match the existing SQLAlchemy ``Session`` layer.

Invariants enforced per request:
- normalize email (done at the schema boundary);
- enforce the 60s resend cooldown against the most recent token;
- atomically invalidate prior unused tokens and create a new one (committed);
- store only the token hash, never the raw token;
- send the email *outside* the DB transaction;
- return an identical response whether or not the email is registered (the service
  never reads the ``users`` table at request time -> no enumeration).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.modules.identity.adapters.email import EmailDeliveryError, EmailSender
from src.modules.identity.exceptions import (
    RESEND_COOLDOWN_SECONDS,
    EmailServiceUnavailableError,
    MagicLinkRateLimitedError,
)
from src.modules.identity.models import MagicLinkToken
from src.modules.identity.repository import MagicLinkTokenRepository
from src.modules.identity.schemas import MagicLinkData

logger = logging.getLogger(__name__)

# --- Module constants (contract-fixed; tests control time, not config) --------

MAGIC_LINK_TTL = timedelta(minutes=15)
RESEND_COOLDOWN = timedelta(seconds=RESEND_COOLDOWN_SECONDS)
MAGIC_LINK_TOKEN_BYTES = 32  # 256 bits of entropy
MAGIC_LINK_SUCCESS_MESSAGE = "Nếu email hợp lệ, liên kết đăng nhập sẽ được gửi."


# --- Token generation + hashing helpers (pure stdlib) -------------------------


def generate_magic_link_token() -> str:
    """Return a high-entropy URL-safe random token."""
    return secrets.token_urlsafe(MAGIC_LINK_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of ``token``.

    The raw token is the secret; hashing means a DB leak yields no usable token.
    256-bit entropy makes an HMAC secret unnecessary.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Service ------------------------------------------------------------------


class MagicLinkService:
    """Orchestrates a magic-link request."""

    def __init__(
        self,
        *,
        session: Session,
        repository: MagicLinkTokenRepository,
        email_sender: EmailSender,
        base_url: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._email_sender = email_sender
        self._base_url = base_url
        self._clock = clock or _utcnow

    def request_magic_link(self, email: str) -> MagicLinkData:
        now = self._clock()

        latest = self._repository.get_most_recent_token(self._session, email)
        if latest is not None and (now - latest.created_at) < RESEND_COOLDOWN:
            raise MagicLinkRateLimitedError(
                resend_after_seconds=int(RESEND_COOLDOWN.total_seconds())
            )

        # Atomic invariant: invalidate prior unused tokens + create a new one.
        self._repository.invalidate_unused_tokens(self._session, email, now)
        raw_token = generate_magic_link_token()
        self._repository.add(
            self._session,
            MagicLinkToken(
                email=email,
                token_hash=hash_token(raw_token),
                expires_at=now + MAGIC_LINK_TTL,
                created_at=now,
                user_id=None,
            ),
        )
        self._session.commit()

        # External I/O happens OUTSIDE the transaction so a provider failure
        # cannot corrupt the token invariant. If email fails, the committed token
        # still expires and is one-time-use (harmless); the caller gets 503 and is
        # rate-limited for the cooldown window (acceptable MVP failure behavior).
        url = f"{self._base_url}/auth/verify?token={raw_token}"
        try:
            self._email_sender.send_magic_link(
                to_email=email,
                magic_link_url=url,
            )
        except EmailDeliveryError:
            # No raw email/token in the log.
            logger.warning("magic_link_email_send_failed")
            raise EmailServiceUnavailableError() from None

        return MagicLinkData(
            message=MAGIC_LINK_SUCCESS_MESSAGE,
            resend_after_seconds=int(RESEND_COOLDOWN.total_seconds()),
        )
