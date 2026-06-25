from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.modules.menu_scan.adapters.storage import (
    ObjectStorage,
    build_object_storage,
)
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.service import ScanService


@lru_cache
def get_object_storage() -> ObjectStorage:
    return build_object_storage(settings.storage)


def get_scan_service(
    session: Session = Depends(get_db),
) -> ScanService:
    return ScanService(
        session=session,
        repository=ScanSessionRepository(),
        storage=get_object_storage(),
    )
