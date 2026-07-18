"""Persistence helpers for dining sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.modules.dining.models import (
    DiningSession,
    DiningSessionInvite,
    DiningSessionParticipant,
)
from src.modules.menu.models import FoodItem, Menu, MenuHostSelection


class DiningSessionRepository:
    def add_session(self, session: Session, dining_session: DiningSession) -> None:
        session.add(dining_session)

    def add_invite(self, session: Session, invite: DiningSessionInvite) -> None:
        session.add(invite)

    def add_participant(
        self,
        session: Session,
        participant: DiningSessionParticipant,
    ) -> None:
        session.add(participant)

    def get_owned(
        self,
        session: Session,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DiningSession | None:
        statement = (
            select(DiningSession)
            .where(
                DiningSession.id == session_id,
                DiningSession.created_by_user_id == user_id,
                DiningSession.deleted_at.is_(None),
            )
            .options(
                selectinload(DiningSession.participants).selectinload(
                    DiningSessionParticipant.preferences
                ),
                selectinload(DiningSession.invites),
            )
        )
        return session.scalars(statement).first()

    def get_owned_with_selections(
        self,
        session: Session,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DiningSession | None:
        """Owned session with each participant's dish picks eager-loaded.

        Backs the host's "who ordered what" view — kept separate from get_owned so
        the plain session detail does not pay for the selection joins.
        """
        statement = (
            select(DiningSession)
            .where(
                DiningSession.id == session_id,
                DiningSession.created_by_user_id == user_id,
                DiningSession.deleted_at.is_(None),
            )
            .options(
                selectinload(DiningSession.participants).selectinload(
                    DiningSessionParticipant.selections
                ),
            )
        )
        return session.scalars(statement).first()

    def list_owned(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
    ) -> list[DiningSession]:
        statement = (
            select(DiningSession)
            .where(
                DiningSession.created_by_user_id == user_id,
                DiningSession.deleted_at.is_(None),
            )
            .order_by(DiningSession.created_at.desc())
            .options(
                selectinload(DiningSession.participants).selectinload(
                    DiningSessionParticipant.preferences
                )
            )
        )
        return list(session.scalars(statement))

    def get_invite_by_hash(
        self,
        session: Session,
        *,
        token_hash: str,
    ) -> DiningSessionInvite | None:
        statement = (
            select(DiningSessionInvite)
            .where(DiningSessionInvite.token_hash == token_hash)
            .options(
                selectinload(DiningSessionInvite.dining_session)
                .selectinload(DiningSession.participants)
                .selectinload(DiningSessionParticipant.preferences),
                selectinload(DiningSessionInvite.dining_session)
                .selectinload(DiningSession.participants)
                .selectinload(DiningSessionParticipant.selections),
                selectinload(DiningSessionInvite.dining_session).selectinload(
                    DiningSession.invites
                ),
            )
        )
        return session.scalars(statement).first()

    def get_owned_by_menu(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DiningSession | None:
        """The caller's dining session that produced this menu, if any.

        Lets the host's menu page discover it is a group session (and so should
        show who ordered what and offer a per-person split).
        """
        statement = select(DiningSession).where(
            DiningSession.menu_id == menu_id,
            DiningSession.created_by_user_id == user_id,
            DiningSession.deleted_at.is_(None),
        )
        return session.scalars(statement).first()

    def list_session_meals(
        self,
        session: Session,
        *,
        session_id: uuid.UUID,
    ) -> list[tuple[Menu, int]]:
        """Every menu (meal) scanned into this session, newest first, with dish
        counts. This is the group's meal history."""
        statement = (
            select(Menu, func.count(FoodItem.id))
            .outerjoin(FoodItem, FoodItem.menu_id == Menu.id)
            .where(
                Menu.dining_session_id == session_id,
                Menu.deleted_at.is_(None),
            )
            .group_by(Menu.id)
            .order_by(Menu.created_at.desc())
        )
        return [(menu, count) for menu, count in session.execute(statement).all()]

    def get_menu(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
    ) -> Menu | None:
        statement = select(Menu).where(
            Menu.id == menu_id,
            Menu.deleted_at.is_(None),
        )
        return session.scalars(statement).first()

    def list_menu_items(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
    ) -> list[FoodItem]:
        statement = (
            select(FoodItem)
            .where(FoodItem.menu_id == menu_id)
            .order_by(FoodItem.sort_order)
        )
        return list(session.scalars(statement))

    def get_owned_session_for_menu(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DiningSession | None:
        """The session this menu belongs to, if the caller owns it — works for any
        meal (uses Menu.dining_session_id, not the session's latest-meal pointer)."""
        statement = (
            select(DiningSession)
            .join(Menu, Menu.dining_session_id == DiningSession.id)
            .where(
                Menu.id == menu_id,
                DiningSession.created_by_user_id == user_id,
                DiningSession.deleted_at.is_(None),
            )
        )
        return session.scalars(statement).first()

    def list_host_selections(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
    ) -> list[MenuHostSelection]:
        statement = select(MenuHostSelection).where(
            MenuHostSelection.menu_id == menu_id
        )
        return list(session.scalars(statement))
