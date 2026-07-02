from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from src.core.responses import success_response
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User
from src.modules.menu.dependencies import get_menu_service
from src.modules.menu.schemas import MenuSavedResponse, UpdateMenuRequest
from src.modules.menu.service import MenuService

router = APIRouter(prefix="/menus", tags=["menus"])


@router.patch("/{menu_id}", status_code=status.HTTP_200_OK)
def update_menu(
    menu_id: uuid.UUID,
    payload: UpdateMenuRequest,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> dict[str, object]:
    menu = service.update_saved_state(
        menu_id=menu_id,
        user_id=current_user.id,
        is_saved=payload.is_saved,
    )
    data = MenuSavedResponse.model_validate(menu)
    return success_response(data=data.model_dump(mode="json"))
