from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.menu.repository import MenuRepository
from src.modules.menu.service import MenuService
from src.modules.menu_scan.dependencies import get_food_enricher


def get_menu_service(session: Session = Depends(get_db)) -> MenuService:
    return MenuService(
        session=session,
        repository=MenuRepository(),
        enricher=get_food_enricher(),
    )
