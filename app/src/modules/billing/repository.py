"""Persistence queries for bills, bill items, and bill adjustments.

Intent-named methods only. The repository never commits -- the service owns
the transaction boundary (same convention as ``modules.identity.repository``).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.billing.models import Bill, BillAdjustment, BillItem


class BillRepository:
    def get_by_id(self, session: Session, bill_id: uuid.UUID) -> Bill | None:
        """Return the bill with its items and adjustments eagerly loaded."""
        statement = (
            select(Bill)
            .where(Bill.id == bill_id)
            .options(
                selectinload(Bill.items),
                selectinload(Bill.adjustments),
            )
        )
        return session.scalars(statement).first()

    def get_by_id_for_user(
        self,
        session: Session,
        bill_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Bill | None:
        """Return the bill only if it belongs to ``user_id``."""
        statement = (
            select(Bill)
            .where(Bill.id == bill_id, Bill.user_id == user_id)
            .options(
                selectinload(Bill.items),
                selectinload(Bill.adjustments),
            )
        )
        return session.scalars(statement).first()

    def list_for_user(self, session: Session, user_id: uuid.UUID) -> list[Bill]:
        """Return every bill owned by ``user_id``, most recent first."""
        statement = (
            select(Bill)
            .where(Bill.user_id == user_id)
            .order_by(Bill.created_at.desc())
        )
        return list(session.scalars(statement).all())

    def add(self, session: Session, bill: Bill) -> Bill:
        """Stage a new bill and flush so its UUID/defaults populate."""
        session.add(bill)
        session.flush()
        return bill

    def add_item(self, session: Session, item: BillItem) -> BillItem:
        """Stage a new bill item and flush."""
        session.add(item)
        session.flush()
        return item

    def add_adjustment(
        self,
        session: Session,
        adjustment: BillAdjustment,
    ) -> BillAdjustment:
        """Stage a new bill adjustment and flush."""
        session.add(adjustment)
        session.flush()
        return adjustment

    def get_adjustment(
        self,
        session: Session,
        bill_id: uuid.UUID,
        adjustment_id: uuid.UUID,
    ) -> BillAdjustment | None:
        """Return the adjustment only if it belongs to ``bill_id``."""
        statement = select(BillAdjustment).where(
            BillAdjustment.id == adjustment_id,
            BillAdjustment.bill_id == bill_id,
        )
        return session.scalars(statement).first()

    def remove_adjustment(
        self,
        session: Session,
        bill: Bill,
        adjustment: BillAdjustment,
    ) -> None:
        """Detach ``adjustment`` from ``bill`` (cascade delete-orphan)."""
        bill.adjustments.remove(adjustment)
        session.flush()

    def clear_items(self, session: Session, bill: Bill) -> None:
        """Delete every existing line item on ``bill`` (cascade delete-orphan)."""
        bill.items.clear()
        session.flush()