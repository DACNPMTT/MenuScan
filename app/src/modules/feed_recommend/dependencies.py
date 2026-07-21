"""FastAPI dependency wiring for the feed_recommend module."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.feed_recommend.service import FeedRecommendService


def get_feed_recommend_service(
    session: Session = Depends(get_db),
) -> FeedRecommendService:
    return FeedRecommendService(session=session)
