from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    price: Decimal | None
    currency: str | None
    category: str | None
    allergens: list[str] = Field(default_factory=list)
    dietary_tags: list[str] = Field(default_factory=list)
    confidence_score: Decimal | None
    sort_order: int

    @field_validator("allergens", "dietary_tags", mode="before")
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
