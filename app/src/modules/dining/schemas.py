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
    name: str | None = Field(default=None, max_length=255)


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
    name: str | None
    created_by_user_id: uuid.UUID | None
    menu_id: uuid.UUID | None = None
    scan_session_id: uuid.UUID | None = None
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
    # Present once the host has scanned a menu into this session; until then the
    # guest can only declare preferences, there are no dishes to pick yet.
    menu_id: uuid.UUID | None = None


# --- Guest dish selection -------------------------------------------------


class SelectionRequest(BaseModel):
    food_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=99)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SetParticipantSelectionsRequest(BaseModel):
    """Replaces a participant's whole selection set (idempotent 'chốt')."""

    participant_id: uuid.UUID
    selections: list[SelectionRequest] = Field(default_factory=list)


class SetParticipantPreferencesRequest(BaseModel):
    """Replaces a participant's whole preference set, so a guest can edit or add
    allergies/tastes after joining."""

    participant_id: uuid.UUID
    preferences: list[DiningPreferenceRequest] = Field(default_factory=list)


class SetHostSelectionsRequest(BaseModel):
    """Replaces the host's own picks for a menu (their order draft)."""

    selections: list[SelectionRequest] = Field(default_factory=list)


class HostSelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    food_item_id: uuid.UUID
    quantity: int
    note: str | None = None


class HostSelectionsResponse(BaseModel):
    menu_id: uuid.UUID
    items: list[HostSelectionResponse] = Field(default_factory=list)


class PublicMenuItemResponse(BaseModel):
    """A dish as a guest sees it — enough to choose from, no host-only fields."""

    id: uuid.UUID
    original_name: str
    translated_name: str | None = None
    translated_description: str | None = None
    assistant_summary: str | None = None
    category: str | None = None
    price: str | None = None
    currency: str | None = None
    allergens: list[str] = Field(default_factory=list)
    # The verdict the host's recommend run scored for this dish (group-level,
    # plus per-participant breakdowns). None until that run has happened, or
    # when nobody declared anything to score against.
    recommendation: RecommendationResponse | None = None


class PublicSessionMenuResponse(BaseModel):
    session_id: uuid.UUID
    menu_id: uuid.UUID | None = None
    title: str | None = None
    default_currency: str | None = None
    status: str
    items: list[PublicMenuItemResponse] = Field(default_factory=list)


# --- Host visibility of what guests picked --------------------------------


class SelectionByParticipantResponse(BaseModel):
    participant_id: uuid.UUID
    display_name: str
    quantity: int
    note: str | None = None


class SelectionSummaryItemResponse(BaseModel):
    food_item_id: uuid.UUID
    total_quantity: int
    selected_by: list[SelectionByParticipantResponse] = Field(default_factory=list)


class SessionSelectionsSummaryResponse(BaseModel):
    session_id: uuid.UUID
    items: list[SelectionSummaryItemResponse] = Field(default_factory=list)


# --- Meals (a session spans several scanned menus) ------------------------


class SessionMealResponse(BaseModel):
    menu_id: uuid.UUID
    title: str | None = None
    default_currency: str | None = None
    status: str
    item_count: int
    created_at: datetime


class SessionMealsResponse(BaseModel):
    session_id: uuid.UUID
    items: list[SessionMealResponse] = Field(default_factory=list)


# --- Guest-facing shared receipt (finalized bills of a session) -----------


class PublicBillItemResponse(BaseModel):
    """One line on a shared receipt, as a guest sees it."""

    name: str
    quantity: int
    line_total: str


class PublicBillAdjustmentResponse(BaseModel):
    """A fee/tax/discount line on a shared receipt. ``amount`` is signed."""

    label: str
    amount: str


class PublicBillResponse(BaseModel):
    """A FINALIZED bill of the session, with its even-split per-person share.

    Read-only: money fields are decimal strings computed server-side. When the
    host recorded a split headcount, ``people_count``/``per_person`` are set so
    the guest sees exactly what they owe; otherwise both are null.
    """

    bill_id: uuid.UUID
    menu_id: uuid.UUID
    menu_title: str | None = None
    currency: str
    subtotal_amount: str
    total_amount: str
    finalized_at: datetime | None = None
    items: list[PublicBillItemResponse] = Field(default_factory=list)
    adjustments: list[PublicBillAdjustmentResponse] = Field(default_factory=list)
    people_count: int | None = None
    per_person: str | None = None


class PublicSessionBillsResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    items: list[PublicBillResponse] = Field(default_factory=list)
