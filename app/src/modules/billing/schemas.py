"""Pydantic schemas for the billing module API boundary.

Money fields are always serialized as decimal strings (contract: see
``doc/content/api-endpoints.md``), never as float, to avoid precision loss.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class CreateBillRequest(BaseModel):
    """Request body for ``POST /bills``."""

    menu_id: uuid.UUID


class BillItemInput(BaseModel):
    """One desired line item inside ``PATCH /bills/{bill_id}/items``.

    The client only ever sends a reference (``food_item_id``) and a
    ``quantity`` -- never a price; the unit price is always re-derived
    server-side from the current ``FoodItem`` row.
    """

    food_item_id: uuid.UUID
    quantity: int = Field(gt=0, description="Số lượng món, phải là số nguyên dương.")


class UpdateBillItemsRequest(BaseModel):
    """Request body for ``PATCH /bills/{bill_id}/items``.

    Represents the *desired end state* of the bill's line items: a food item
    present here is added or updated to that quantity; any existing line
    whose food item is absent from ``items`` is removed. An empty list clears
    the bill back to a zero subtotal.
    """

    items: list[BillItemInput] = Field(default_factory=list)


class BillItemResponse(BaseModel):
    """One bill line item in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    food_item_id: uuid.UUID | None
    name_snapshot: str
    unit_price_snapshot: Decimal
    currency: str
    quantity: int
    line_total: Decimal
    sort_order: int

    @field_serializer("unit_price_snapshot", "line_total")
    def _serialize_money(self, value: Decimal) -> str:
        return str(value)


class BillResponse(BaseModel):
    """Full bill representation, including line items, in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    menu_id: uuid.UUID
    status: str
    currency: str
    subtotal_amount: Decimal
    adjustment_total: Decimal
    total_amount: Decimal
    note: str | None
    items: list[BillItemResponse]
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None

    @field_serializer("subtotal_amount", "adjustment_total", "total_amount")
    def _serialize_money(self, value: Decimal) -> str:
        return str(value)

    @field_serializer("status")
    def _serialize_status(self, value: object) -> str:
        return value.value if hasattr(value, "value") else str(value)