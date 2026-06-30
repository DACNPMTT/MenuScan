"""Bill API endpoints (see GitHub issue #128).

Router only parses/validates the request, delegates to ``BillingService`` and
maps the result -- all business rules (ownership, mutability, totals) live in
the service.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from src.core.responses import success_response
from src.modules.billing.dependencies import get_billing_service
from src.modules.billing.schemas import (
    BillResponse,
    CreateBillRequest,
    UpdateBillItemsRequest,
)
from src.modules.billing.service import BillingService
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: CreateBillRequest,
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
) -> dict[str, object]:
    """Create an empty DRAFT bill for the current user, scoped to a menu."""
    bill = service.create_bill(user_id=current_user.id, menu_id=payload.menu_id)
    data = BillResponse.model_validate(bill)
    return success_response(data=data.model_dump(mode="json"))


@router.get("/{bill_id}", status_code=status.HTTP_200_OK)
def get_bill(
    bill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
) -> dict[str, object]:
    """Retrieve a bill with its line items. Only the owner may access it."""
    bill = service.get_bill_for_user(bill_id=bill_id, user_id=current_user.id)
    data = BillResponse.model_validate(bill)
    return success_response(data=data.model_dump(mode="json"))


@router.patch("/{bill_id}/items", status_code=status.HTTP_200_OK)
def update_bill_items(
    bill_id: uuid.UUID,
    payload: UpdateBillItemsRequest,
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
) -> dict[str, object]:
    """Add, update, or remove bill items in one call and recompute totals.

    ``payload.items`` is the desired end state: omit a food item to remove
    it, change its ``quantity`` to update it, and add a new entry to add it.
    """
    items = [(item.food_item_id, item.quantity) for item in payload.items]
    bill = service.replace_items(
        bill_id=bill_id,
        user_id=current_user.id,
        items=items,
    )
    data = BillResponse.model_validate(bill)
    return success_response(data=data.model_dump(mode="json"))