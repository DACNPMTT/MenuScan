from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.modules.dining.schemas import (  # noqa: F401 — re-exported for existing importers
    ParticipantBreakdownResponse,
    RecommendationResponse,
)
from src.modules.menu_scan.models import ScanStatus


class ScanSourceData(BaseModel):
    file_name: str
    mime_type: str
    file_size: int


class ScanCreatedData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ScanStatus
    progress: int
    source: ScanSourceData
    target_language: str
    created_at: datetime


class ScanStatusData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ScanStatus
    stage: str | None
    progress: int
    error: dict[str, str | None] | None
    created_at: datetime
    completed_at: datetime | None


class ScanListSourceData(BaseModel):
    file_name: str
    mime_type: str
    file_size: int
    preview_url: str


class ScanListMenuData(BaseModel):
    id: UUID
    title: str
    is_saved: bool
    item_count: int


class ScanListItemData(BaseModel):
    id: UUID
    status: ScanStatus
    created_at: datetime
    completed_at: datetime | None
    source: ScanListSourceData
    menu: ScanListMenuData | None


class MenuItemData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_name: str
    translated_name: str | None
    original_description: str | None
    translated_description: str | None
    assistant_summary: str | None = None
    main_ingredients: list[str] = Field(default_factory=list)
    ingredient_tags: list[str] = Field(default_factory=list)
    flavor_tags: list[str] = Field(default_factory=list)
    texture_tags: list[str] = Field(default_factory=list)
    cooking_methods: list[str] = Field(default_factory=list)
    spice_level: int | None = None
    sweetness_level: int | None = None
    saltiness_level: int | None = None
    sourness_level: int | None = None
    richness_level: int | None = None
    oiliness_level: int | None = None
    risk_notes: str | None = None
    price: Decimal | None
    currency: str | None
    category: str | None
    allergens: list[str] = Field(default_factory=list)
    dietary_tags: list[str] = Field(default_factory=list)
    confidence_score: Decimal | None
    sort_order: int
    recommendation: RecommendationResponse | None = None

    @field_validator(
        "allergens",
        "dietary_tags",
        "main_ingredients",
        "ingredient_tags",
        "flavor_tags",
        "texture_tags",
        "cooking_methods",
        mode="before",
    )
    @classmethod
    def _coerce_none_to_list(cls, value: object) -> object:
        return value if value is not None else []


class MenuResultData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    default_currency: str | None
    is_saved: bool
    items: list[MenuItemData]


class ScanResultSourceData(BaseModel):
    file_name: str
    mime_type: str
    file_size: int
    preview_url: str


class ScanResultScanData(BaseModel):
    id: UUID
    status: ScanStatus
    source: ScanResultSourceData
    detected_language: str | None
    target_language: str
    processing_time_ms: int | None


class ScanResultData(BaseModel):
    scan: ScanResultScanData
    menu: MenuResultData | None
