"""Pydantic schemas for the identity module API boundary."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class MagicLinkRequest(BaseModel):
    """Request body for ``POST /auth/magic-links``.

    Normalizes at the boundary: trim whitespace, then lowercase, so the service
    receives a canonical email. Invalid format -> Pydantic -> ``validation_error_handler``
    -> ``400 VALIDATION_ERROR`` with ``details.fields.email``.
    """

    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def _strip_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email", mode="after")
    @classmethod
    def _lowercase_email(cls, value: str) -> str:
        return value.lower()


class MagicLinkData(BaseModel):
    """Response data for a magic-link request."""

    message: str
    resend_after_seconds: int
