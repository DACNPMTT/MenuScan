from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.menu.models import FoodItem, Menu


class MenuRepository:
    def get_by_id(self, session: Session, *, menu_id: uuid.UUID) -> Menu | None:
        statement = (
            select(Menu)
            .options(selectinload(Menu.scan_session))
            .where(Menu.id == menu_id)
        )
        return session.scalars(statement).first()

    def save_menu_with_items(
        self,
        session: Session,
        menu: Menu,
        food_items: list[FoodItem],
    ) -> None:
        """Persist a menu and its food items atomically."""
        session.add(menu)
        session.flush()
        for item in food_items:
            item.menu_id = menu.id
        session.add_all(food_items)
        session.flush()

    def save(self, session: Session, menu: Menu) -> Menu:
        session.add(menu)
        session.flush()
        return menu
