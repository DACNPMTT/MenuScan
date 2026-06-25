from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.menu_scan.models import ScanStatus


class ScanSourceData(BaseModel):
    file_name: str
    mime_type: str
    file_size: int


class ScanCreatedData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ScanStatus
    progress: int
    source: ScanSourceData
    target_language: str
    created_at: datetime


class ScanStatusData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ScanStatus
    stage: str | None
    progress: int
    error: dict[str, str | None] | None
    created_at: datetime
    completed_at: datetime | None
