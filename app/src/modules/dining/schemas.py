"""Pydantic schemas for dining-session APIs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class ParticipantBreakdownResponse(BaseModel):
    display_name: str
    verdict: str
    score: float | None = None
    explanation: str | None = None
    fit_reasons: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """A dish's verdict for the diner(s) looking at it.

    Absent (None on the item) when nobody has told us anything to score against —
    a verdict with no evidence behind it is worse than no verdict.
    """

    verdict: str
    score: float | None = None
    explanation: str | None = None
    why_suitable: str | None = None
    why_not_suitable: str | None = None
    suggested_for: list[str] = Field(default_factory=list)
    warning_for: list[str] = Field(default_factory=list)
    fit_reasons: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)
    warning_reasons: list[str] = Field(default_factory=list)
    participant_breakdowns: list[ParticipantBreakdownResponse] = Field(
        default_factory=list
    )


FoodPreferenceType = Literal[
    "LIKE",
    "DISLIKE",
    "AVOID",
    "ALLERGY",
    "DIETARY_RULE",
]


class DiningPreferenceRequest(BaseModel):
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


class CreateDiningSessionRequest(BaseModel):
    mode: Literal["GROUP", "PERSONAL"] = "GROUP"
    invite_expires_in_hours: int | None = Field(default=12, ge=1, le=168)


class JoinDiningSessionRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=150)
    preferences: list[DiningPreferenceRequest] = Field(default_factory=list)

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class DiningPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    category: str
    preference_type: str
    intensity: int | None
    importance: int
    note: str | None
    created_at: datetime


class DiningParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dining_session_id: uuid.UUID
    display_name: str
    joined_at: datetime
    left_at: datetime | None
    preferences: list[DiningPreferenceResponse] = Field(default_factory=list)


class DiningSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    mode: str
    status: str
    participant_count: int = 0
    participants: list[DiningParticipantResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    closed_at: datetime | None

    @model_validator(mode="after")
    def _set_participant_count(self) -> DiningSessionResponse:
        self.participant_count = len(self.participants)
        return self


class DiningSessionInviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dining_session_id: uuid.UUID
    expires_at: datetime | None
    max_uses: int | None
    use_count: int
    created_at: datetime


class CreateDiningSessionResponse(BaseModel):
    session: DiningSessionResponse
    invite: DiningSessionInviteResponse
    invite_token: str


class PublicDiningSessionResponse(BaseModel):
    session_id: uuid.UUID
    mode: str
    status: str
    participant_count: int
    created_at: datetime
