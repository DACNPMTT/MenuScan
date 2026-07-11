"""Persistence helpers for dining sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.dining.models import (
    DiningSession,
    DiningSessionInvite,
    DiningSessionParticipant,
)


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
                selectinload(DiningSessionInvite.dining_session).selectinload(
                    DiningSession.participants
                ),
                selectinload(DiningSessionInvite.dining_session).selectinload(
                    DiningSession.invites
                ),
            )
        )
        return session.scalars(statement).first()
