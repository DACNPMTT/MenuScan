from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.modules.menu.models import FoodItem, Menu


class MenuRepository:
    def get_by_id(self, session: Session, *, menu_id: uuid.UUID) -> Menu | None:
        statement = (
            select(Menu)
            .options(selectinload(Menu.scan_session), selectinload(Menu.food_items))
            .where(Menu.id == menu_id, Menu.deleted_at.is_(None))
        )
        return session.scalars(statement).first()

    def list_for_user(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> list[tuple[Menu, int]]:
        statement = (
            select(Menu, func.count(FoodItem.id).label("item_count"))
            .join(Menu.scan_session)
            .outerjoin(FoodItem, FoodItem.menu_id == Menu.id)
            .options(selectinload(Menu.scan_session))
            .where(
                Menu.deleted_at.is_(None),
                Menu.scan_session.has(user_id=user_id),
            )
            .group_by(Menu.id)
            .order_by(desc(Menu.updated_at), desc(Menu.created_at), desc(Menu.id))
            .limit(limit)
            .offset(offset)
        )
        return [(row[0], row[1]) for row in session.execute(statement).all()]

    def count_for_user(self, session: Session, *, user_id: uuid.UUID) -> int:
        statement = (
            select(func.count())
            .select_from(Menu)
            .where(
                Menu.deleted_at.is_(None),
                Menu.scan_session.has(user_id=user_id),
            )
        )
        return session.scalar(statement) or 0

    def list_items_for_menu(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
        search: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        limit: int,
        offset: int,
    ) -> list[FoodItem]:
        statement = (
            self._items_for_menu_statement(
                menu_id=menu_id,
                search=search,
                min_price=min_price,
                max_price=max_price,
            )
            .order_by(FoodItem.sort_order, FoodItem.id)
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(statement).all())

    def count_items_for_menu(
        self,
        session: Session,
        *,
        menu_id: uuid.UUID,
        search: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(FoodItem)
            .where(
                *self._items_for_menu_filters(
                    menu_id=menu_id,
                    search=search,
                    min_price=min_price,
                    max_price=max_price,
                )
            )
        )
        return session.scalar(statement) or 0

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

    def save_item(self, session: Session, item: FoodItem) -> FoodItem:
        session.add(item)
        session.flush()
        return item

    def delete_item(self, session: Session, item: FoodItem) -> None:
        session.delete(item)
        session.flush()

    def _items_for_menu_statement(
        self,
        *,
        menu_id: uuid.UUID,
        search: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ):
        return select(FoodItem).where(
            *self._items_for_menu_filters(
                menu_id=menu_id,
                search=search,
                min_price=min_price,
                max_price=max_price,
            )
        )

    def _items_for_menu_filters(
        self,
        *,
        menu_id: uuid.UUID,
        search: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> list[object]:
        filters: list[object] = [FoodItem.menu_id == menu_id]
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(FoodItem.original_name).like(pattern),
                    func.lower(FoodItem.translated_name).like(pattern),
                )
            )
        if min_price is not None:
            filters.append(FoodItem.price.is_not(None))
            filters.append(FoodItem.price >= min_price)
        if max_price is not None:
            filters.append(FoodItem.price.is_not(None))
            filters.append(FoodItem.price <= max_price)
        return filters
