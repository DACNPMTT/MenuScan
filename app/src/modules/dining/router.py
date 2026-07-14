"""FastAPI router for dining-session workflows."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, status

from src.core.responses import success_response
from src.modules.dining.dependencies import get_dining_session_service
from src.modules.dining.schemas import (
    CreateDiningSessionRequest,
    CreateDiningSessionResponse,
    DiningSessionResponse,
    JoinDiningSessionRequest,
    DiningParticipantResponse,
    PublicDiningSessionResponse,
)
from src.modules.dining.service import DiningSessionService
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


@router.delete("/sessions/{session_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    data = DiningParticipantResponse.model_validate(participant).model_dump(
        mode="json"
    )
    return success_response(data=data)
