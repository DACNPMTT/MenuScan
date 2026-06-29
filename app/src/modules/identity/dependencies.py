"""FastAPI dependency wiring for the identity module."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import SessionLocal, get_db
from src.modules.identity.adapters.email import (
    ConsoleEmailSender,
    EmailSender,
    ResendEmailSender,
)
from src.modules.identity.exceptions import UnauthorizedError
from src.modules.identity.models import User, UserStatus
from src.modules.identity.repository import MagicLinkTokenRepository, UserRepository, UserSessionRepository
from src.modules.identity.service import MagicLinkService, decode_access_token

oauth2_scheme = HTTPBearer(auto_error=False)


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
        user_repository=UserRepository(),
        session_repository=UserSessionRepository(),
        secret_key=settings.secret_key,
    )


def require_bearer_credentials(
    token: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
) -> HTTPAuthorizationCredentials:
    if token is None or token.scheme.lower() != "bearer":
        raise UnauthorizedError()
    return token


def require_valid_access_token(request: Request) -> None:
    """Validate a signed access token before private routers are reached."""
    user_override = request.app.dependency_overrides.get(get_current_user)
    if user_override is not None:
        request.state.current_user = user_override()
        return

    authorization = request.headers.get("authorization")
    scheme, separator, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        raise UnauthorizedError()

    user_id = decode_access_token(
        token=token,
        secret_key=settings.secret_key,
    )

    db_override = request.app.dependency_overrides.get(get_db)
    if db_override is not None:
        session = db_override()
        should_close = False
    else:
        session = SessionLocal()
        should_close = True

    try:
        user = UserRepository().get_by_id(session, user_id)
        if (
            user is None
            or user.status != UserStatus.ACTIVE
            or user.deleted_at is not None
        ):
            raise UnauthorizedError()
        request.state.current_user = user
    finally:
        if should_close:
            session.close()


def get_authenticated_user(request: Request) -> User:
    user = getattr(request.state, "current_user", None)
    if not isinstance(user, User):
        raise UnauthorizedError()
    return user


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(require_bearer_credentials),
    session: Session = Depends(get_db),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> User:
    """FastAPI dependency to retrieve and validate the current authenticated user."""
    user_id = service.decode_access_token(token.credentials)
    user_repo = UserRepository()
    user = user_repo.get_by_id(session, user_id)

    if user is None or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
        raise UnauthorizedError()

    return user
