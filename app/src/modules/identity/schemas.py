"""Pydantic schemas for the identity module API boundary."""

from __future__ import annotations

import uuid
from datetime import datetime

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


class MagicLinkVerifyRequest(BaseModel):
    """Request body for ``POST /auth/magic-links/verify``."""

    token: str


class SetPasswordRequest(BaseModel):
    """Request body for setting the password after verification."""

    password: str


class LoginRequest(BaseModel):
    """Request body for traditional email/password login."""

    email: EmailStr
    password: str

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


class UserResponse(BaseModel):
    """User representation inside the auth responses."""

    id: uuid.UUID
    email: str
    display_name: str | None
    preferred_language: str
    role: str

    class Config:
        from_attributes = True


class MagicLinkVerifyResponse(BaseModel):
    """Response payload for successful magic-link verification."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
    user: UserResponse


class RefreshResponse(BaseModel):
    """Response payload for token refresh."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 900


class UserMeResponse(BaseModel):
    """Full user profile response for ``GET /auth/me``."""

    id: uuid.UUID
    email: str
    display_name: str | None
    preferred_language: str
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
