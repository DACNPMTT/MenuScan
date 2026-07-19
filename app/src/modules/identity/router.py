import logging
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from src.core.config import settings
from src.core.responses import success_response
from src.modules.identity.cookies import (
    clear_refresh_token_cookie,
    set_refresh_token_cookie,
)
from src.modules.identity.dependencies import get_current_user, get_magic_link_service
from src.modules.identity.exceptions import UnauthorizedError
from src.modules.identity.models import User
from src.modules.identity.schemas import (
    ConfirmDeleteRequest,
    CreateFoodProfileRequest,
    FoodProfileResponse,
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    SetPasswordRequest,
    UpdateUserProfileRequest,
    UpdateFoodProfileRequest,
)
from src.modules.identity.service import MagicLinkService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def verify_origin(request: Request) -> None:
    """CSRF defense for cookie-only endpoints (notably /auth/refresh).

    SameSite=Lax/Strict already blocks cross-site POST cookie submission, so
    this is a no-op unless SESSION_COOKIE_SAMESITE=none (cross-origin prod).
    In that mode we require the browser-controlled Origin (or Referer) header
    to match the CORS allowlist — an attacker page can submit a form but cannot
    forge Origin. A missing Origin (non-browser client) is allowed: there is no
    cookie-submitting browser in the loop, hence no CSRF surface.
    """
    if settings.session_cookie_samesite != "none":
        return
    raw = request.headers.get("origin") or request.headers.get("referer")
    if not raw:
        return
    parsed = urlparse(raw)
    candidate = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if candidate not in settings.cors_origins:
        logger.debug("origin_rejected origin=%s", raw)
        raise UnauthorizedError()


def _user_response_data(
    user: User, *, include_profile_details: bool = False
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "preferred_language": user.preferred_language,
        "allergies": list(user.allergies or []),
        "dietary_preferences": list(user.dietary_preferences or []),
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


def _food_profile_response_data(profile: object) -> dict[str, object]:
    return FoodProfileResponse.model_validate(profile).model_dump(mode="json")


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
    _: None = Depends(verify_origin),
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
    return success_response(
        data=_user_response_data(user, include_profile_details=True)
    )


@router.post("/me/profile", status_code=status.HTTP_200_OK)
def update_me_profile(
    payload: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """POST-compatible profile update for clients/proxies that block PATCH."""
    updates = payload.model_dump(exclude_unset=True)
    user = service.update_user_profile(current_user, **updates)
    return success_response(
        data=_user_response_data(user, include_profile_details=True)
    )


@router.get("/me/food-profiles", status_code=status.HTTP_200_OK)
def list_food_profiles(
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """List persistent food profiles owned by the current user."""
    profiles = service.list_food_profiles(current_user)
    return success_response(
        data=[_food_profile_response_data(profile) for profile in profiles]
    )


@router.post("/me/food-profiles", status_code=status.HTTP_201_CREATED)
def create_food_profile(
    payload: CreateFoodProfileRequest,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Create a persistent food profile for the current user."""
    profile = service.create_food_profile(
        current_user,
        display_name=payload.display_name,
        preferred_language=payload.preferred_language,
        is_default=payload.is_default,
        notes=payload.notes,
        preferences=payload.preferences,
    )
    return success_response(data=_food_profile_response_data(profile))


@router.get("/me/food-profiles/{profile_id}", status_code=status.HTTP_200_OK)
def get_food_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Retrieve one food profile owned by the current user."""
    profile = service.get_food_profile(current_user, profile_id=profile_id)
    return success_response(data=_food_profile_response_data(profile))


@router.patch("/me/food-profiles/{profile_id}", status_code=status.HTTP_200_OK)
def update_food_profile(
    profile_id: uuid.UUID,
    payload: UpdateFoodProfileRequest,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Update a persistent food profile owned by the current user."""
    updates = {}
    if "display_name" in payload.model_fields_set:
        updates["display_name"] = payload.display_name
    if "preferred_language" in payload.model_fields_set:
        updates["preferred_language"] = payload.preferred_language
    if "is_default" in payload.model_fields_set:
        updates["is_default"] = payload.is_default
    if "notes" in payload.model_fields_set:
        updates["notes"] = payload.notes
    if "preferences" in payload.model_fields_set:
        updates["preferences"] = payload.preferences
    profile = service.update_food_profile(
        current_user,
        profile_id=profile_id,
        **updates,
    )
    return success_response(data=_food_profile_response_data(profile))


@router.delete(
    "/me/food-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_food_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> None:
    """Soft-delete one food profile owned by the current user."""
    service.delete_food_profile(current_user, profile_id=profile_id)


@router.post("/me/delete-request", status_code=status.HTTP_202_ACCEPTED)
def request_account_deletion(
    current_user: User = Depends(get_current_user),
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Send a delete-confirmation email to the current user."""
    service.request_account_deletion(current_user)
    return success_response(
        data={"message": "Email xác nhận xoá tài khoản đã được gửi."}
    )


@router.post("/confirm-delete", status_code=status.HTTP_200_OK)
def confirm_account_deletion(
    payload: ConfirmDeleteRequest,
    service: MagicLinkService = Depends(get_magic_link_service),
) -> dict[str, object]:
    """Verify the delete token and soft-delete the user account."""
    service.confirm_account_deletion(payload.token)
    return success_response(data={"message": "Tài khoản đã được xoá thành công."})
