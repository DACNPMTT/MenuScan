"""Pydantic schemas for the identity module API boundary."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
)

# Dietary taxonomy the diner may declare. Allergies mirror the allergen tags the
# parser assigns to dishes; dietary preferences are avoidance rules matched
# against each dish's dietary_tags.
ALLERGEN_CODES = frozenset(
    {
        "seafood", "shellfish", "fish", "peanut", "tree_nut",
        "egg", "dairy", "gluten", "soy", "sesame",
    }
)
DIETARY_PREFERENCE_CODES = frozenset(
    {"vegetarian", "vegan", "no_pork", "no_beef", "no_alcohol"}
)


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


class UpdateUserProfileRequest(BaseModel):
    """Request body for updating editable profile preferences."""

    display_name: str | None = None
    preferred_language: Literal["vi", "en"] | None = None
    allergies: list[str] | None = None
    dietary_preferences: list[str] | None = None

    @field_validator("allergies", "dietary_preferences", mode="after")
    @classmethod
    def _validate_dietary_codes(
        cls, value: list[str] | None, info: ValidationInfo
    ) -> list[str] | None:
        if value is None:
            return None
        allowed = (
            ALLERGEN_CODES
            if info.field_name == "allergies"
            else DIETARY_PREFERENCE_CODES
        )
        cleaned: list[str] = []
        for raw in value:
            code = str(raw).strip().lower()
            if not code or code in cleaned:
                continue
            if code not in allowed:
                raise ValueError(f"Unknown {info.field_name} code: {code}")
            cleaned.append(code)
        return cleaned

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("display_name", mode="after")
    @classmethod
    def _validate_display_name_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 150:
            raise ValueError("Display name must be 150 characters or fewer.")
        return value

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _normalize_preferred_language(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


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


FoodPreferenceType = Literal[
    "LIKE",
    "DISLIKE",
    "AVOID",
    "ALLERGY",
    "DIETARY_RULE",
]


class FoodProfilePreferenceRequest(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    preference_type: FoodPreferenceType
    intensity: int | None = Field(default=None, ge=0, le=5)
    importance: int = Field(default=3, ge=1, le=5)
    note: str | None = None

    @field_validator("code", "category", mode="before")
    @classmethod
    def _normalize_code_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CreateFoodProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=150)
    preferred_language: str = Field(default="vi", min_length=2, max_length=10)
    is_default: bool = False
    notes: str | None = None
    preferences: list[FoodProfilePreferenceRequest] = Field(default_factory=list)

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _normalize_language(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class UpdateFoodProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=150)
    preferred_language: str | None = Field(default=None, min_length=2, max_length=10)
    is_default: bool | None = None
    notes: str | None = None
    preferences: list[FoodProfilePreferenceRequest] | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _normalize_language(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class FoodProfilePreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    category: str
    preference_type: str
    intensity: int | None
    importance: int
    note: str | None
    created_at: datetime


class FoodProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    preferred_language: str
    is_default: bool
    notes: str | None
    preferences: list[FoodProfilePreferenceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseModel):
    """User representation inside the auth responses."""

    id: uuid.UUID
    email: str
    display_name: str | None
    preferred_language: str
    allergies: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
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
    allergies: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
