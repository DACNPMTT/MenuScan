"""Persistence queries for the feed_recommend module.

Intent-named methods only. The repository never commits — the service owns
the transaction boundary (same rule as ``identity.repository``).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.modules.feed_recommend.models import (
    UserLocation,
    UserRestaurantSave,
    UserRestaurantSeen,
)


class UserLocationRepository:
    def get(
        self,
        session: Session,
        user_id: uuid.UUID,
    ) -> UserLocation | None:
        return session.scalars(
            select(UserLocation).where(UserLocation.user_id == user_id)
        ).first()

    def upsert(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        lat: float,
        lng: float,
        address_text: str | None,
        source: str,
    ) -> UserLocation:
        """Insert or replace the user's single location row.

        Uses PG ``INSERT ... ON CONFLICT (user_id) DO UPDATE`` so the row is
        always exactly one per user; updated_at refreshes via ``onupdate``.
        """
        statement = (
            pg_insert(UserLocation)
            .values(
                user_id=user_id,
                lat=lat,
                lng=lng,
                address_text=address_text,
                source=source,
            )
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "lat": lat,
                    "lng": lng,
                    "address_text": address_text,
                    "source": source,
                },
            )
            .returning(UserLocation)
        )
        result = session.execute(statement).scalar_one()
        session.flush()
        return result


class UserRestaurantSaveRepository:
    def list(
        self,
        session: Session,
        user_id: uuid.UUID,
    ) -> list[UserRestaurantSave]:
        statement = (
            select(UserRestaurantSave)
            .where(UserRestaurantSave.user_id == user_id)
            .order_by(UserRestaurantSave.saved_at.desc())
        )
        return list(session.scalars(statement))

    def source_ids(self, session: Session, user_id: uuid.UUID) -> set[int]:
        statement = select(UserRestaurantSave.restaurant_source_id).where(
            UserRestaurantSave.user_id == user_id
        )
        return set(session.scalars(statement))

    def add(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        restaurant_source_id: int,
        note: str | None = None,
    ) -> UserRestaurantSave:
        save = UserRestaurantSave(
            user_id=user_id,
            restaurant_source_id=restaurant_source_id,
            note=note,
        )
        session.add(save)
        session.flush()
        return save

    def remove(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        restaurant_source_id: int,
    ) -> bool:
        existing = session.scalars(
            select(UserRestaurantSave).where(
                UserRestaurantSave.user_id == user_id,
                UserRestaurantSave.restaurant_source_id == restaurant_source_id,
            )
        ).first()
        if existing is None:
            return False
        session.delete(existing)
        session.flush()
        return True


class UserRestaurantSeenRepository:
    def source_ids(self, session: Session, user_id: uuid.UUID) -> set[int]:
        statement = select(UserRestaurantSeen.restaurant_source_id).where(
            UserRestaurantSeen.user_id == user_id
        )
        return set(session.scalars(statement))

    def mark(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        restaurant_source_id: int,
        action: str,
    ) -> None:
        """Idempotent: first interaction wins; later calls are no-ops.

        Uses PG ``ON CONFLICT DO NOTHING`` so the UNIQUE(user_id,
        restaurant_source_id) constraint short-circuits duplicate INSERTs.
        """
        statement = (
            pg_insert(UserRestaurantSeen)
            .values(
                user_id=user_id,
                restaurant_source_id=restaurant_source_id,
                action=action,
            )
            .on_conflict_do_nothing(
                index_elements=["user_id", "restaurant_source_id"]
            )
        )
        session.execute(statement)
        session.flush()
