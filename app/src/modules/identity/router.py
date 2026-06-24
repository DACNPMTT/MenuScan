from fastapi import APIRouter, Depends, status

from src.core.responses import success_response
from src.modules.identity.dependencies import get_magic_link_service
from src.modules.identity.schemas import MagicLinkRequest
from src.modules.identity.service import MagicLinkService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-links", status_code=status.HTTP_202_ACCEPTED)
def request_magic_link(
    payload: MagicLinkRequest,
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Request a magic-login link.

    Returns an identical 202 response whether or not the email is registered.
    Validation / rate-limit / email-failure errors flow through the standard
    handlers.
    """
    data = service.request_magic_link(payload.email)
    return success_response(data=data.model_dump())
