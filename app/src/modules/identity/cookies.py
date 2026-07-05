"""Shared `refresh_token` cookie attributes — single source of truth so the
three set-cookie call sites (magic-link verify, login, refresh) and the
delete-cookie call site (logout) can't drift from each other."""

from fastapi import Response

from src.core.config import settings
from src.modules.identity.service import SESSION_TTL

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"


def _cookie_secure() -> bool:
    return settings.app_env != "development" and settings.app_env != "test"


def set_refresh_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
        max_age=int(SESSION_TTL.total_seconds()),
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )
