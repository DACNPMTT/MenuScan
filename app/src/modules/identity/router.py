from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from src.core.responses import success_response
from src.modules.identity.cookies import (
    clear_refresh_token_cookie,
    set_refresh_token_cookie,
)
from src.modules.identity.dependencies import get_current_user, get_magic_link_service
from src.modules.identity.models import User
from src.modules.identity.schemas import (
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    SetPasswordRequest,
    UpdateUserProfileRequest,
)
from src.modules.identity.service import MagicLinkService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response_data(user: User, *, include_profile_details: bool = False) -> dict[str, object]:
    data: dict[str, object] = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "preferred_language": user.preferred_language,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    }
    if include_profile_details:
        data.update(
            {
                "status": user.status.value
                if hasattr(user.status, "value")
                else str(user.status),
                "created_at": user.created_at,
            }
        )
    return data


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


@router.post("/magic-links/verify", status_code=status.HTTP_200_OK)
def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    response: Response,
    request: Request,
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Verify a magic link token, establish a session and set refresh cookie."""
    user_agent = request.headers.get("user-agent")

    access_token, user, refresh_token = service.verify_magic_link(
        token=payload.token,
        user_agent=user_agent,
    )

    set_refresh_token_cookie(response, refresh_token)

    return success_response(
        data={
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 900,
            "user": _user_response_data(user),
        }
    )


@router.post("/set-password", status_code=status.HTTP_200_OK)
def set_password(
    payload: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Set or update password for the currently logged-in user."""
    service.set_user_password(current_user, payload.password)
    return success_response(data={"message": "Mật khẩu đã được thiết lập thành công."})


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Authenticate user with email and password, establish a session and set refresh cookie."""
    user_agent = request.headers.get("user-agent")

    access_token, user, refresh_token = service.login_with_password(
        email=payload.email,
        password=payload.password,
        user_agent=user_agent,
    )

    set_refresh_token_cookie(response, refresh_token)

    return success_response(
        data={
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 900,
            "user": _user_response_data(user),
        }
    )


@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_session(
    response: Response,
    request: Request,
    refresh_token: str | None = Cookie(default=None),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Rotate the refresh token cookie and issue a new access token."""
    user_agent = request.headers.get("user-agent")

    new_access_token, new_refresh_token = service.refresh_session(
        refresh_token_cookie=refresh_token,
        user_agent=user_agent,
    )

    set_refresh_token_cookie(response, new_refresh_token)

    return success_response(
        data={
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 900,
        }
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> None:
    """Idempotently revoke the current session and clear cookies."""
    service.logout(refresh_token)
    clear_refresh_token_cookie(response)


@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Retrieve details for the currently authenticated user."""
    return success_response(
        data=_user_response_data(current_user, include_profile_details=True)
    )


@router.patch("/me", status_code=status.HTTP_200_OK)
def update_me(
    payload: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Update editable profile fields for the currently authenticated user."""
    updates = payload.model_dump(exclude_unset=True)
    user = service.update_user_profile(current_user, **updates)
    return success_response(data=_user_response_data(user, include_profile_details=True))


@router.post("/me/profile", status_code=status.HTTP_200_OK)
def update_me_profile(
    payload: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """POST-compatible profile update for clients/proxies that block PATCH."""
    updates = payload.model_dump(exclude_unset=True)
    user = service.update_user_profile(current_user, **updates)
    return success_response(data=_user_response_data(user, include_profile_details=True))
