from __future__ import annotations

from sqlalchemy.orm import Session

from src.modules.menu.models import FoodItem, Menu


class MenuRepository:
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
