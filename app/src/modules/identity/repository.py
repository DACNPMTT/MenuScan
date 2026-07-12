"""Persistence queries for magic-link tokens.

Intent-named methods only. The repository never commits — the service owns the
transaction boundary (rule: service owns commit).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from src.modules.identity.models import (
    FoodProfile,
    FoodProfilePreference,
    MagicLinkToken,
    User,
    UserSession,
)


class MagicLinkTokenRepository:
    def get_most_recent_token(
        self,
        session: Session,
        email: str,
    ) -> MagicLinkToken | None:
        """Return the most recently created token for ``email``, or ``None``."""
        statement = (
            select(MagicLinkToken)
            .where(MagicLinkToken.email == email)
            .order_by(MagicLinkToken.created_at.desc())
            .limit(1)
        )
        return session.scalars(statement).first()

    def get_token_by_hash(
        self,
        session: Session,
        token_hash: str,
    ) -> MagicLinkToken | None:
        """Return the token with the given SHA-256 hash, or ``None``."""
        statement = select(MagicLinkToken).where(
            MagicLinkToken.token_hash == token_hash
        )
        return session.scalars(statement).first()

    def invalidate_unused_tokens(
        self,
        session: Session,
        email: str,
        now: datetime,
    ) -> None:
        """Mark every still-unused token for ``email`` as consumed.

        A token is valid only while ``consumed_at IS NULL``; both "used to log in"
        and "superseded by a newer request" set ``consumed_at`` (Decision 1 in the
        request-endpoint plan). Uses the index on ``(email, created_at)``.
        """
        session.execute(
            update(MagicLinkToken)
            .where(
                MagicLinkToken.email == email,
                MagicLinkToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )

    def add(self, session: Session, token: MagicLinkToken) -> None:
        """Stage a new token and flush so server defaults populate."""
        session.add(token)
        session.flush()


class UserRepository:
    def get_by_email(self, session: Session, email: str) -> User | None:
        """Retrieve a user by email, case-insensitively."""
        statement = select(User).where(func.lower(User.email) == func.lower(email))
        return session.scalars(statement).first()

    def get_by_id(self, session: Session, user_id: uuid.UUID) -> User | None:
        """Retrieve a user by their UUID."""
        statement = select(User).where(User.id == user_id)
        return session.scalars(statement).first()

    def create(self, session: Session, user: User) -> User:
        """Stage a new user record and flush so UUID and server defaults populate."""
        session.add(user)
        session.flush()
        return user


class UserSessionRepository:
    def get_by_id(self, session: Session, session_id: uuid.UUID) -> UserSession | None:
        """Retrieve a session by its UUID."""
        statement = select(UserSession).where(UserSession.id == session_id)
        return session.scalars(statement).first()

    def add(self, session: Session, user_session: UserSession) -> None:
        """Stage a new session record and flush."""
        session.add(user_session)
        session.flush()


class FoodProfileRepository:
    def list_by_user(self, session: Session, user_id: uuid.UUID) -> list[FoodProfile]:
        statement = (
            select(FoodProfile)
            .options(selectinload(FoodProfile.preferences))
            .where(FoodProfile.user_id == user_id, FoodProfile.deleted_at.is_(None))
            .order_by(FoodProfile.is_default.desc(), FoodProfile.updated_at.desc())
        )
        return list(session.scalars(statement))

    def get_owned(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> FoodProfile | None:
        statement = (
            select(FoodProfile)
            .options(selectinload(FoodProfile.preferences))
            .where(
                FoodProfile.id == profile_id,
                FoodProfile.user_id == user_id,
                FoodProfile.deleted_at.is_(None),
            )
        )
        return session.scalars(statement).first()

    def has_active_profiles(self, session: Session, user_id: uuid.UUID) -> bool:
        statement = (
            select(FoodProfile.id)
            .where(FoodProfile.user_id == user_id, FoodProfile.deleted_at.is_(None))
            .limit(1)
        )
        return session.scalars(statement).first() is not None

    def clear_default(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        exclude_profile_id: uuid.UUID | None = None,
    ) -> None:
        statement = (
            update(FoodProfile)
            .where(
                FoodProfile.user_id == user_id,
                FoodProfile.deleted_at.is_(None),
                FoodProfile.is_default.is_(True),
            )
            .values(is_default=False)
        )
        if exclude_profile_id is not None:
            statement = statement.where(FoodProfile.id != exclude_profile_id)
        session.execute(statement)

    def add(self, session: Session, profile: FoodProfile) -> FoodProfile:
        session.add(profile)
        session.flush()
        return profile

    def replace_preferences(
        self,
        session: Session,
        profile: FoodProfile,
        preferences: list[FoodProfilePreference],
    ) -> None:
        profile.preferences.clear()
        session.flush()
        profile.preferences.extend(preferences)
        session.flush()
