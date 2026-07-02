from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UpdateMenuRequest(BaseModel):
    is_saved: bool


class MenuSavedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_saved: bool
    updated_at: datetime
