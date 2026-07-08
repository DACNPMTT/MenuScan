from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.modules.menu.models import MenuStatus


class UpdateMenuRequest(BaseModel):
    is_saved: bool


class CreateMenuItemRequest(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)
    translated_name: str | None = Field(default=None, max_length=255)
    original_description: str | None = None
    translated_description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    category: str | None = Field(default=None, max_length=100)

    @field_validator("original_name")
    @classmethod
    def original_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("original_name must not be blank")
        return value


class UpdateMenuItemRequest(BaseModel):
    original_name: str | None = Field(default=None, min_length=1, max_length=255)
    translated_name: str | None = Field(default=None, max_length=255)
    original_description: str | None = None
    translated_description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    category: str | None = Field(default=None, max_length=100)

    @field_validator("original_name")
    @classmethod
    def original_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("original_name must not be blank")
        return value


class ListMenuItemsQuery(BaseModel):
    search: str | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_price_range(self) -> "ListMenuItemsQuery":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class MenuSavedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_saved: bool
    updated_at: datetime


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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


class MenuSourceResponse(BaseModel):
    scan_id: uuid.UUID
    file_name: str
    mime_type: str
    file_size: int
    preview_url: str


class MenuSummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: MenuStatus
    is_saved: bool
    item_count: int
    default_currency: str | None
    source: MenuSourceResponse
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None


class MenuDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: MenuStatus
    is_saved: bool
    source_language: str | None
    target_language: str
    default_currency: str | None
    source: MenuSourceResponse
    items: list[MenuItemResponse]
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None
