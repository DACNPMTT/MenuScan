"""FastAPI dependency wiring for the identity module."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.modules.identity.adapters.email import (
    ConsoleEmailSender,
    EmailSender,
    ResendEmailSender,
)
from src.modules.identity.repository import MagicLinkTokenRepository
from src.modules.identity.service import MagicLinkService


@lru_cache
def get_email_sender() -> EmailSender:
    """Process-wide email sender selected by ``EMAIL_PROVIDER``.

    - ``console`` (default): logs the link, never raises.
    - ``resend``: calls the Resend API; config is validated at startup
      (``Settings.from_environment`` fails fast if the key/from are missing).

    Tests override via ``app.dependency_overrides``.
    """
    config = settings.email
    if config.provider == "console":
        return ConsoleEmailSender()
    if config.provider == "resend":
        # Validated non-empty at startup; guard keeps mypy/type narrow happy.
        assert config.api_key is not None  # noqa: S101
        return ResendEmailSender(
            api_key=config.api_key,
            from_address=config.from_address,
            api_base_url=config.api_base_url,
            timeout_seconds=config.timeout_seconds,
        )
    raise ValueError(f"Unsupported EMAIL_PROVIDER={config.provider!r}")


def get_magic_link_service(
    session: Session = Depends(get_db),
) -> MagicLinkService:
    repository = MagicLinkTokenRepository()
    return MagicLinkService(
        session=session,
        repository=repository,
        email_sender=get_email_sender(),
        base_url=settings.magic_link_base_url,
    )
