"""Shared `refresh_token` cookie attributes — single source of truth so the
three set-cookie call sites (magic-link verify, login, refresh) and the
delete-cookie call site (logout) can't drift from each other.

``SESSION_COOKIE_SAMESITE`` (env, default ``lax``) picks the SameSite value:
``lax`` is safe for same-origin deployments and gives CSRF protection for free.
``none`` is only for cross-origin production; then CSRF defense shifts to the
Origin check wired into the /auth/refresh and /auth/logout endpoints.
``Secure`` follows ``APP_ENV`` (off in development/test so cookies work over
plain HTTP locally; on everywhere else).
"""

from fastapi import Response

from src.core.config import settings
from src.modules.identity.service import SESSION_TTL

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"


def _cookie_secure() -> bool:
    """Mirror cookies only over HTTPS outside development/test."""
    return settings.app_env not in {"development", "test"}


def _cookie_attrs() -> dict[str, object]:
    return {
        "key": REFRESH_TOKEN_COOKIE_NAME,
        "httponly": True,
        "samesite": settings.session_cookie_samesite,
        "secure": _cookie_secure(),
        "path": "/",
    }


def set_refresh_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        **_cookie_attrs(),
        value=token,
        max_age=int(SESSION_TTL.total_seconds()),
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(**_cookie_attrs())
