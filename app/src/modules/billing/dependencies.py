"""FastAPI dependency wiring for the billing module."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.billing.repository import BillRepository
from src.modules.billing.service import BillingService


def get_billing_service(session: Session = Depends(get_db)) -> BillingService:
    return BillingService(session=session, repository=BillRepository())
