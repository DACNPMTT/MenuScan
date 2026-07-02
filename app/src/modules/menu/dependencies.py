from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.menu.repository import MenuRepository
from src.modules.menu.service import MenuService


def get_menu_service(session: Session = Depends(get_db)) -> MenuService:
    return MenuService(session=session, repository=MenuRepository())
