"""FastAPI router for dining-session workflows."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, status

from src.core.responses import success_response
from src.modules.dining.dependencies import get_dining_session_service
from src.modules.dining.exceptions import DiningSessionNotFoundError
from src.modules.dining.schemas import (
    CreateDiningSessionRequest,
    CreateDiningSessionResponse,
    DiningSessionResponse,
    JoinDiningSessionRequest,
    DiningParticipantResponse,
    HostSelectionResponse,
    HostSelectionsResponse,
    PublicDiningSessionResponse,
    PublicMenuItemResponse,
    PublicSessionMenuResponse,
    SelectionByParticipantResponse,
    SelectionSummaryItemResponse,
    SessionMealResponse,
    SessionMealsResponse,
    SessionSelectionsSummaryResponse,
    SetHostSelectionsRequest,
    SetParticipantPreferencesRequest,
    SetParticipantSelectionsRequest,
)
from src.modules.dining.service import DiningSessionService, SelectionItem
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

router = APIRouter(prefix="/dining", tags=["dining"])


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: CreateDiningSessionRequest,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Create a new dining session with an invite token."""
    bundle = service.create_session(
        current_user,
        mode=payload.mode,
        invite_expires_in_hours=payload.invite_expires_in_hours,
        name=payload.name,
    )
    response_data = CreateDiningSessionResponse(
        session=DiningSessionResponse.model_validate(bundle.dining_session),
        invite=bundle.invite,
        invite_token=bundle.invite_token,
    )
    return success_response(data=response_data.model_dump(mode="json"))


@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """List dining sessions created by the current user."""
    sessions = service.list_sessions(current_user)
    data = [
        DiningSessionResponse.model_validate(s).model_dump(mode="json")
        for s in sessions
    ]
    return success_response(data=data)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Retrieve session details (including participants)."""
    session = service.get_session(current_user, session_id=session_id)
    data = DiningSessionResponse.model_validate(session).model_dump(mode="json")
    return success_response(data=data)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> None:
    """Soft-delete a dining session."""
    service.delete_session(current_user, session_id=session_id)


@router.delete(
    "/sessions/{session_id}/participants/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_participant(
    session_id: uuid.UUID,
    participant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> None:
    """Remove a participant from a dining session."""
    service.remove_participant(
        current_user,
        session_id=session_id,
        participant_id=participant_id,
    )


@router.post("/sessions/{session_id}/close")
def close_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Host closes the session: no more joins or dish-pick changes."""
    session = service.set_session_closed(
        current_user, session_id=session_id, closed=True
    )
    data = DiningSessionResponse.model_validate(session).model_dump(mode="json")
    return success_response(data=data)


@router.post("/sessions/{session_id}/open")
def open_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Host reopens a closed session so guests can order again."""
    session = service.set_session_closed(
        current_user, session_id=session_id, closed=False
    )
    data = DiningSessionResponse.model_validate(session).model_dump(mode="json")
    return success_response(data=data)


@router.get("/menus/{menu_id}/host-selections")
def get_host_selections(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """The host's own saved picks for a menu (their order draft)."""
    rows = service.get_host_selections(current_user, menu_id=menu_id)
    response_data = HostSelectionsResponse(
        menu_id=menu_id,
        items=[HostSelectionResponse.model_validate(row) for row in rows],
    )
    return success_response(data=response_data.model_dump(mode="json"))


@router.put("/menus/{menu_id}/host-selections")
def set_host_selections(
    menu_id: uuid.UUID,
    payload: SetHostSelectionsRequest,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Replace the host's picks for a menu so they persist across reloads."""
    selections = [
        SelectionItem(
            food_item_id=sel.food_item_id,
            quantity=sel.quantity,
            note=sel.note,
        )
        for sel in payload.selections
    ]
    rows = service.set_host_selections(
        current_user, menu_id=menu_id, selections=selections
    )
    return success_response(data={"updated": len(rows)})


@router.get("/sessions/{session_id}/meals")
def list_session_meals(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """The session's meals — every menu scanned into it, newest first."""
    rows = service.list_session_meals(current_user, session_id=session_id)
    response_data = SessionMealsResponse(
        session_id=session_id,
        items=[
            SessionMealResponse(
                menu_id=menu.id,
                title=menu.title,
                default_currency=menu.default_currency,
                status=menu.status.value,
                item_count=item_count,
                created_at=menu.created_at,
            )
            for menu, item_count in rows
        ],
    )
    return success_response(data=response_data.model_dump(mode="json"))


@router.get("/sessions/by-menu/{menu_id}")
def get_session_by_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Resolve the caller's dining session for a menu (404 if it is not one).

    The host's menu page calls this to learn whether the menu came from a group
    session — and so whether to show guest picks and the per-person split.
    """
    session = service.get_session_by_menu(current_user, menu_id=menu_id)
    if session is None:
        raise DiningSessionNotFoundError()
    return success_response(
        data={
            "session_id": str(session.id),
            "status": session.status.value,
            "mode": session.mode.value,
        }
    )


@router.get("/public/sessions")
def get_public_session(
    invite_token: str = Query(..., min_length=1),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Get public session overview by invite token (auth-free)."""
    session = service.get_public_session(invite_token=invite_token)
    response_data = PublicDiningSessionResponse(
        session_id=session.id,
        mode=session.mode.value,
        status=session.status.value,
        participant_count=len(session.participants),
        created_at=session.created_at,
        menu_id=session.menu_id,
    )
    return success_response(data=response_data.model_dump(mode="json"))


@router.post("/public/sessions/join", status_code=status.HTTP_201_CREATED)
def join_session(
    payload: JoinDiningSessionRequest,
    invite_token: str = Query(..., min_length=1),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Join a dining session by token and declare preferences (auth-free)."""
    participant = service.join_with_invite(
        invite_token=invite_token,
        display_name=payload.display_name,
        preferences=payload.preferences,
    )
    data = DiningParticipantResponse.model_validate(participant).model_dump(mode="json")
    return success_response(data=data)


@router.put("/public/sessions/{session_id}/preferences")
def set_participant_preferences(
    session_id: uuid.UUID,
    payload: SetParticipantPreferencesRequest,
    invite_token: str = Query(..., min_length=1),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Guest edits/adds their preferences after joining (auth-free, idempotent)."""
    participant = service.set_participant_preferences(
        session_id=session_id,
        invite_token=invite_token,
        participant_id=payload.participant_id,
        preferences=payload.preferences,
    )
    data = DiningParticipantResponse.model_validate(participant).model_dump(mode="json")
    return success_response(data=data)


@router.get("/public/sessions/{session_id}/menu")
def get_public_session_menu(
    session_id: uuid.UUID,
    invite_token: str = Query(..., min_length=1),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """The dishes a guest can pick from (auth-free, gated by the invite token)."""
    session, menu, items = service.get_public_menu(
        session_id=session_id,
        invite_token=invite_token,
    )
    response_data = PublicSessionMenuResponse(
        session_id=session.id,
        menu_id=session.menu_id,
        title=menu.title if menu is not None else None,
        default_currency=menu.default_currency if menu is not None else None,
        status=session.status.value,
        items=[
            PublicMenuItemResponse(
                id=item.id,
                original_name=item.original_name,
                translated_name=item.translated_name,
                translated_description=item.translated_description,
                assistant_summary=item.assistant_summary,
                category=item.category,
                price=str(item.price) if item.price is not None else None,
                currency=item.currency,
                allergens=list(item.allergens or []),
            )
            for item in items
        ],
    )
    return success_response(data=response_data.model_dump(mode="json"))


@router.put("/public/sessions/{session_id}/selections")
def set_participant_selections(
    session_id: uuid.UUID,
    payload: SetParticipantSelectionsRequest,
    invite_token: str = Query(..., min_length=1),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Replace a participant's dish picks (auth-free, idempotent)."""
    selections = [
        SelectionItem(
            food_item_id=sel.food_item_id,
            quantity=sel.quantity,
            note=sel.note,
        )
        for sel in payload.selections
    ]
    saved = service.set_participant_selections(
        session_id=session_id,
        invite_token=invite_token,
        participant_id=payload.participant_id,
        selections=selections,
    )
    return success_response(data={"updated": len(saved)})


@router.get("/sessions/{session_id}/selections")
def get_session_selections(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DiningSessionService = Depends(get_dining_session_service),
) -> dict[str, object]:
    """Host view: which participant picked which dish, and how many."""
    session = service.get_selections_summary(current_user, session_id=session_id)

    grouped: dict[uuid.UUID, dict[str, object]] = {}
    for participant in session.participants:
        for selection in participant.selections:
            entry = grouped.setdefault(
                selection.food_item_id,
                {"total_quantity": 0, "selected_by": []},
            )
            entry["total_quantity"] = int(entry["total_quantity"]) + selection.quantity
            selected_by = entry["selected_by"]
            assert isinstance(selected_by, list)
            selected_by.append(
                SelectionByParticipantResponse(
                    participant_id=participant.id,
                    display_name=participant.display_name,
                    quantity=selection.quantity,
                    note=selection.note,
                )
            )

    response_data = SessionSelectionsSummaryResponse(
        session_id=session.id,
        items=[
            SelectionSummaryItemResponse(
                food_item_id=food_item_id,
                total_quantity=int(entry["total_quantity"]),
                selected_by=entry["selected_by"],  # type: ignore[arg-type]
            )
            for food_item_id, entry in grouped.items()
        ],
    )
    return success_response(data=response_data.model_dump(mode="json"))
