"""Shared `refresh_token` cookie attributes — single source of truth so the
three set-cookie call sites (magic-link verify, login, refresh) and the
delete-cookie call site (logout) can't drift from each other."""

from fastapi import Response

from src.core.config import settings
from src.modules.identity.service import SESSION_TTL

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"


def _cookie_secure() -> bool:
    # On production (or whenever it's not dev/test), we must use Secure=True
    # especially when SameSite=None is set for cross-origin requests.
    return settings.app_env != "development" and settings.app_env != "test"


def set_refresh_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        path="/",
        max_age=int(SESSION_TTL.total_seconds()),
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="none",
        secure=True,
    )
