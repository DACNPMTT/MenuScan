from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from src.core.responses import success_response
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User
from src.modules.menu.dependencies import get_menu_service
from src.modules.menu.schemas import (
    CreateMenuItemRequest,
    MenuSavedResponse,
    UpdateMenuItemRequest,
    UpdateMenuRequest,
)
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


@router.post("/{menu_id}/confirm", status_code=status.HTTP_200_OK)
def confirm_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> dict[str, object]:
    data = service.confirm_menu(menu_id=menu_id, user_id=current_user.id)
    return success_response(data=data.model_dump(mode="json"))


@router.get("", status_code=status.HTTP_200_OK)
def list_menus(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> dict[str, object]:
    items, total = service.list_menus(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get("/{menu_id}", status_code=status.HTTP_200_OK)
def get_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> dict[str, object]:
    data = service.get_menu(menu_id=menu_id, user_id=current_user.id)
    return success_response(data=data.model_dump(mode="json"))


@router.post("/{menu_id}/items", status_code=status.HTTP_201_CREATED)
def create_menu_item(
    menu_id: uuid.UUID,
    payload: CreateMenuItemRequest,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> dict[str, object]:
    data = service.create_menu_item(
        menu_id=menu_id,
        user_id=current_user.id,
        payload=payload,
    )
    return success_response(data=data.model_dump(mode="json"))


@router.patch("/{menu_id}/items/{item_id}", status_code=status.HTTP_200_OK)
def update_menu_item(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: UpdateMenuItemRequest,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> dict[str, object]:
    data = service.update_menu_item(
        menu_id=menu_id,
        item_id=item_id,
        user_id=current_user.id,
        payload=payload,
    )
    return success_response(data=data.model_dump(mode="json"))


@router.delete("/{menu_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> Response:
    service.delete_menu_item(
        menu_id=menu_id,
        item_id=item_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
) -> Response:
    service.delete_menu(menu_id=menu_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
