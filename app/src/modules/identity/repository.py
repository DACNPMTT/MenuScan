"""Persistence queries for magic-link tokens.

Intent-named methods only. The repository never commits — the service owns the
transaction boundary (rule: service owns commit).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.modules.identity.models import MagicLinkToken


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
