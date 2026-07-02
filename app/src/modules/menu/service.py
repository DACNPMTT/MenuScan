from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.modules.menu.exceptions import MenuForbiddenError, MenuNotFoundError
from src.modules.menu.models import Menu
from src.modules.menu.repository import MenuRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MenuService:
    def __init__(
        self,
        *,
        session: Session,
        repository: MenuRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._clock = clock or _utcnow

    def update_saved_state(
        self,
        *,
        menu_id: uuid.UUID,
        user_id: uuid.UUID,
        is_saved: bool,
    ) -> Menu:
        menu = self._repository.get_by_id(self._session, menu_id=menu_id)
        if menu is None:
            raise MenuNotFoundError()
        if menu.scan_session.user_id != user_id:
            raise MenuForbiddenError()

        now = self._clock()
        menu.is_saved = is_saved
        menu.saved_at = now if is_saved else None
        menu.updated_at = now
        self._repository.save(self._session, menu)
        self._session.commit()
        return menu
