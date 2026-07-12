from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.errors import DependencyUnavailableError
from src.core.rate_limit import enforce_chat_throttle, refund
from src.core.responses import success_response
from src.modules.advisor.adapters.gemini_chat import ChatProviderError
from src.modules.advisor.dependencies import get_advisor_service
from src.modules.advisor.schemas import ChatRequest, ChatResponse
from src.modules.advisor.service import AdvisorService
from src.modules.identity.dependencies import get_current_user
from src.modules.identity.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/chat", status_code=status.HTTP_200_OK)
def chat(
    payload: ChatRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _throttle: None = Depends(enforce_chat_throttle),
    service: AdvisorService = Depends(get_advisor_service),
) -> dict[str, object]:
    """Answer a question about a scanned menu, grounded on its dishes + profile.

    Login required (throttled). History is client-supplied and never stored.
    """
    try:
        answer = service.chat(
            user=current_user,
            menu_id=payload.menu_id,
            question=payload.question,
            history=payload.history,
            focus_dishes=payload.focus_dishes,
        )
    except ChatProviderError as error:
        logger.warning("advisor_chat_failed reason=%s", error)
        # The cooldown was spent before the provider was called. It failed, so the
        # diner never got their answer — do not also make them wait out a penalty
        # for a turn they did not use.
        refund(
            session,
            subject_type="user",
            subject_id=str(current_user.id),
            action="chat",
        )
        raise DependencyUnavailableError("advisor") from error
    return success_response(data=ChatResponse(answer=answer).model_dump())
