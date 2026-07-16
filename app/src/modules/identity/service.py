"""Magic-link and session lifecycle workflow.

Synchronous to match the existing SQLAlchemy ``Session`` layer.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from src.core.config import settings
from src.modules.identity.adapters.email import EmailDeliveryError, EmailSender
from src.modules.identity.exceptions import (
    RESEND_COOLDOWN_SECONDS,
    EmailServiceUnavailableError,
    FoodProfileNotFoundError,
    InvalidCredentialsError,
    InvalidMagicLinkError,
    MagicLinkExpiredError,
    MagicLinkRateLimitedError,
    SessionExpiredError,
    SessionRevokedError,
    UnauthorizedError,
)
from src.modules.identity.models import (
    FoodProfile,
    FoodProfilePreference,
    MagicLinkToken,
    PreferenceType,
    User,
    UserRole,
    UserSession,
    UserStatus,
)
from src.modules.identity.repository import (
    FoodProfileRepository,
    MagicLinkTokenRepository,
    UserRepository,
    UserSessionRepository,
)
from src.modules.identity.schemas import (
    FoodProfilePreferenceRequest,
    MagicLinkData,
)

logger = logging.getLogger(__name__)

# --- Module constants (contract-fixed; tests control time, not config) --------

MAGIC_LINK_TTL = timedelta(minutes=15)
RESEND_COOLDOWN = timedelta(seconds=RESEND_COOLDOWN_SECONDS)
MAGIC_LINK_TOKEN_BYTES = 32  # 256 bits of entropy
MAGIC_LINK_SUCCESS_MESSAGE = "Nếu email hợp lệ, liên kết đăng nhập sẽ được gửi."
SESSION_TTL = timedelta(minutes=15)
ACCESS_TOKEN_TTL = timedelta(minutes=15)
_UNSET = object()


# --- Token generation + hashing helpers (pure stdlib) -------------------------


def generate_magic_link_token() -> str:
    """Return a high-entropy URL-safe random token."""
    return secrets.token_urlsafe(MAGIC_LINK_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of ``token``.

    The raw token is the secret; hashing means a DB leak yields no usable token.
    256-bit entropy makes an HMAC secret unnecessary.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Password hashing and verification helpers --------------------------------


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str | None) -> bool:
    """Verify a password against its bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# --- Service ------------------------------------------------------------------


class MagicLinkService:
    """Orchestrates magic-link requests and session management."""

    def __init__(
        self,
        *,
        session: Session,
        repository: MagicLinkTokenRepository,
        email_sender: EmailSender,
        base_url: str,
        user_repository: UserRepository | None = None,
        session_repository: UserSessionRepository | None = None,
        food_profile_repository: FoodProfileRepository | None = None,
        secret_key: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._email_sender = email_sender
        self._base_url = base_url
        self._user_repository = user_repository or UserRepository()
        self._session_repository = session_repository or UserSessionRepository()
        self._food_profile_repository = (
            food_profile_repository or FoodProfileRepository()
        )
        self._secret_key = secret_key or settings.secret_key
        self._clock = clock or _utcnow

    # --- Access Token (JWT) logic ---------------------------------------------

    def create_access_token(self, user_id: uuid.UUID) -> str:
        """Create a signed JWT access token for the given user_id."""
        now = self._clock()
        payload = {
            "sub": str(user_id),
            "exp": int((now + ACCESS_TOKEN_TTL).timestamp()),
            "type": "access",
            "iat": int(now.timestamp()),
        }
        return jwt.encode(payload, self._secret_key, algorithm="HS256")

    def decode_access_token(self, token: str) -> uuid.UUID:
        """Decode and validate a JWT access token, returning the user_id."""
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            if payload.get("type") != "access":
                raise UnauthorizedError()

            exp = payload.get("exp")
            if exp is None or self._clock().timestamp() > exp:
                raise UnauthorizedError()

            sub = payload.get("sub")
            if not sub:
                raise UnauthorizedError()
            return uuid.UUID(sub)
        except (jwt.InvalidTokenError, ValueError) as error:
            logger.debug("access_token_validation_failed error=%r", error)
            raise UnauthorizedError() from error

    # --- Magic Link Request ---------------------------------------------------

    def request_magic_link(self, email: str) -> MagicLinkData:
        now = self._clock()

        latest = self._repository.get_most_recent_token(self._session, email)
        if latest is not None and (now - latest.created_at) < RESEND_COOLDOWN:
            raise MagicLinkRateLimitedError(
                resend_after_seconds=int(RESEND_COOLDOWN.total_seconds())
            )

        # Atomic invariant: invalidate prior unused tokens + create a new one.
        self._repository.invalidate_unused_tokens(self._session, email, now)
        raw_token = generate_magic_link_token()
        self._repository.add(
            self._session,
            MagicLinkToken(
                email=email,
                token_hash=hash_token(raw_token),
                expires_at=now + MAGIC_LINK_TTL,
                created_at=now,
                user_id=None,
            ),
        )
        self._session.commit()

        # External I/O happens OUTSIDE the transaction so a provider failure
        # cannot corrupt the token invariant. If email fails, the committed token
        # still expires and is one-time-use (harmless); the caller gets 503 and is
        # rate-limited for the cooldown window (acceptable MVP failure behavior).
        url = f"{self._base_url}/auth/verify?token={raw_token}"
        user = self._user_repository.get_by_email(self._session, email)
        lang = user.preferred_language if user else "vi"

        try:
            self._email_sender.send_magic_link(
                to_email=email,
                magic_link_url=url,
                lang=lang,
            )
        except EmailDeliveryError:
            # No raw email/token in the log.
            logger.warning("magic_link_email_send_failed")
            raise EmailServiceUnavailableError() from None

        return MagicLinkData(
            message=MAGIC_LINK_SUCCESS_MESSAGE,
            resend_after_seconds=int(RESEND_COOLDOWN.total_seconds()),
        )

    # --- Magic Link Verification ----------------------------------------------

    def verify_magic_link(
        self,
        token: str,
        user_agent: str | None = None,
    ) -> tuple[str, User, str]:
        """Verify the magic link token, create/retrieve user, and create session."""
        now = self._clock()
        token_hash = hash_token(token)
        token_record = self._repository.get_token_by_hash(self._session, token_hash)

        if token_record is None or token_record.consumed_at is not None:
            raise InvalidMagicLinkError()

        if now > token_record.expires_at:
            raise MagicLinkExpiredError()

        # Execute in a transaction block
        user = self._user_repository.get_by_email(self._session, token_record.email)
        if user is None:
            user = User(
                email=token_record.email,
                status=UserStatus.ACTIVE,
                role=UserRole.USER,
                preferred_language="vi",
                created_at=now,
                updated_at=now,
            )
            self._user_repository.create(self._session, user)

        # Mark token as consumed and link to user
        token_record.consumed_at = now
        token_record.user_id = user.id

        # Create session record
        session_id = uuid.uuid4()
        raw_token_secret = secrets.token_urlsafe(32)
        hashed_refresh = hash_token(raw_token_secret)

        user_session = UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hashed_refresh,
            user_agent=user_agent,
            expires_at=now + SESSION_TTL,
            created_at=now,
            last_rotated_at=now,
        )
        self._session_repository.add(self._session, user_session)
        self._session.commit()

        # Build access token
        access_token = self.create_access_token(user.id)
        refresh_token_cookie = f"{session_id}.{raw_token_secret}"

        return access_token, user, refresh_token_cookie

    def set_user_password(self, user: User, password: str) -> None:
        """Hash and set the user's password."""
        now = self._clock()
        user.password_hash = hash_password(password)
        user.updated_at = now
        self._session.commit()

    def update_user_profile(
        self,
        user: User,
        *,
        display_name: str | None | object = _UNSET,
        preferred_language: str | object = _UNSET,
        allergies: list[str] | object = _UNSET,
        dietary_preferences: list[str] | object = _UNSET,
    ) -> User:
        """Update editable profile fields for the currently authenticated user."""
        now = self._clock()
        if display_name is not _UNSET:
            user.display_name = display_name if isinstance(display_name, str) else None
        if preferred_language is not _UNSET and isinstance(preferred_language, str):
            user.preferred_language = preferred_language
        if allergies is not _UNSET and isinstance(allergies, list):
            user.allergies = allergies
        if dietary_preferences is not _UNSET and isinstance(dietary_preferences, list):
            user.dietary_preferences = dietary_preferences
        user.updated_at = now
        self._session.commit()
        return user

    def list_food_profiles(self, user: User) -> list[FoodProfile]:
        """Return active food profiles owned by the current user."""
        return self._food_profile_repository.list_by_user(self._session, user.id)

    def get_food_profile(
        self,
        user: User,
        *,
        profile_id: uuid.UUID,
    ) -> FoodProfile:
        """Return one food profile owned by the current user."""
        profile = self._food_profile_repository.get_owned(
            self._session,
            user_id=user.id,
            profile_id=profile_id,
        )
        if profile is None:
            raise FoodProfileNotFoundError()
        return profile

    def create_food_profile(
        self,
        user: User,
        *,
        display_name: str,
        preferred_language: str,
        is_default: bool,
        notes: str | None,
        preferences: list[FoodProfilePreferenceRequest],
    ) -> FoodProfile:
        """Create a persistent food profile for a signed-in user."""
        now = self._clock()
        should_be_default = is_default or not self._food_profile_repository.has_active_profiles(
            self._session,
            user.id,
        )
        if should_be_default:
            self._food_profile_repository.clear_default(self._session, user_id=user.id)

        profile = FoodProfile(
            user_id=user.id,
            display_name=display_name,
            preferred_language=preferred_language,
            is_default=should_be_default,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        profile.preferences = self._build_food_profile_preferences(preferences)
        self._food_profile_repository.add(self._session, profile)

        if profile.is_default:
            self._sync_user_dietary_snapshot_from_profile(user, profile)
        user.updated_at = now
        self._session.commit()
        return profile

    def update_food_profile(
        self,
        user: User,
        *,
        profile_id: uuid.UUID,
        display_name: str | None | object = _UNSET,
        preferred_language: str | object = _UNSET,
        is_default: bool | object = _UNSET,
        notes: str | None | object = _UNSET,
        preferences: list[FoodProfilePreferenceRequest] | object = _UNSET,
    ) -> FoodProfile:
        """Update a food profile owned by the current user."""
        profile = self._food_profile_repository.get_owned(
            self._session,
            user_id=user.id,
            profile_id=profile_id,
        )
        if profile is None:
            raise FoodProfileNotFoundError()

        now = self._clock()
        if display_name is not _UNSET and isinstance(display_name, str):
            profile.display_name = display_name
        if preferred_language is not _UNSET and isinstance(preferred_language, str):
            profile.preferred_language = preferred_language
        if notes is not _UNSET:
            profile.notes = notes if isinstance(notes, str) else None
        if is_default is not _UNSET and isinstance(is_default, bool):
            if is_default:
                self._food_profile_repository.clear_default(
                    self._session,
                    user_id=user.id,
                    exclude_profile_id=profile.id,
                )
            profile.is_default = is_default
        if preferences is not _UNSET and isinstance(preferences, list):
            self._food_profile_repository.replace_preferences(
                self._session,
                profile,
                self._build_food_profile_preferences(preferences),
            )

        profile.updated_at = now
        user.updated_at = now
        if profile.is_default:
            self._sync_user_dietary_snapshot_from_profile(user, profile)
        self._session.commit()
        return profile

    def delete_food_profile(self, user: User, *, profile_id: uuid.UUID) -> None:
        """Soft-delete a food profile owned by the current user."""
        profile = self._food_profile_repository.get_owned(
            self._session,
            user_id=user.id,
            profile_id=profile_id,
        )
        if profile is None:
            raise FoodProfileNotFoundError()

        now = self._clock()
        was_default = profile.is_default
        profile.deleted_at = now
        profile.is_default = False
        profile.updated_at = now
        user.updated_at = now

        if was_default:
            self._session.flush()
            remaining = self._food_profile_repository.list_by_user(self._session, user.id)
            next_default = next(
                (item for item in remaining if item.id != profile.id),
                None,
            )
            if next_default is not None:
                next_default.is_default = True
                next_default.updated_at = now
                self._sync_user_dietary_snapshot_from_profile(user, next_default)
            else:
                user.allergies = []
                user.dietary_preferences = []

        self._session.commit()

    @staticmethod
    def _build_food_profile_preferences(
        preferences: list[FoodProfilePreferenceRequest],
    ) -> list[FoodProfilePreference]:
        seen: set[tuple[str, str]] = set()
        records: list[FoodProfilePreference] = []
        for item in preferences:
            if isinstance(item, dict):
                code = str(item["code"])
                category = str(item["category"])
                preference_type = str(item["preference_type"])
                intensity = item.get("intensity")
                importance = int(item.get("importance", 3))
                note = item.get("note")
            else:
                code = item.code
                category = item.category
                preference_type = item.preference_type
                intensity = item.intensity
                importance = item.importance
                note = item.note

            key = (code, preference_type)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                FoodProfilePreference(
                    code=code,
                    category=category,
                    preference_type=PreferenceType(preference_type),
                    intensity=intensity,
                    importance=importance,
                    note=note,
                )
            )
        return records

    @staticmethod
    def _sync_user_dietary_snapshot_from_profile(
        user: User,
        profile: FoodProfile,
    ) -> None:
        user.allergies = [
            item.code
            for item in profile.preferences
            if item.preference_type == PreferenceType.ALLERGY
        ]
        user.dietary_preferences = [
            item.code
            for item in profile.preferences
            if item.preference_type == PreferenceType.DIETARY_RULE
        ]

    # --- Traditional Password Login -------------------------------------------

    def login_with_password(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
    ) -> tuple[str, User, str]:
        """Authenticate user with email and password, establishing a session."""
        now = self._clock()
        user = self._user_repository.get_by_email(self._session, email)

        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        if user.status != UserStatus.ACTIVE or user.deleted_at is not None:
            raise UnauthorizedError()

        # Create session record
        session_id = uuid.uuid4()
        raw_token_secret = secrets.token_urlsafe(32)
        hashed_refresh = hash_token(raw_token_secret)

        user_session = UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hashed_refresh,
            user_agent=user_agent,
            expires_at=now + SESSION_TTL,
            created_at=now,
            last_rotated_at=now,
        )
        self._session_repository.add(self._session, user_session)
        self._session.commit()

        # Build access token
        access_token = self.create_access_token(user.id)
        refresh_token_cookie = f"{session_id}.{raw_token_secret}"

        return access_token, user, refresh_token_cookie

    # --- Session Refreshing (RTR) ---------------------------------------------

    def refresh_session(
        self,
        refresh_token_cookie: str | None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        """Rotate the refresh token and issue a new access token."""
        now = self._clock()

        if not refresh_token_cookie or "." not in refresh_token_cookie:
            logger.debug("refresh_failed reason=missing_or_invalid_cookie")
            raise SessionExpiredError()

        try:
            session_id_str, raw_token_secret = refresh_token_cookie.split(".", 1)
            session_id = uuid.UUID(session_id_str)
        except ValueError:
            logger.debug("refresh_failed reason=invalid_cookie_format")
            raise SessionExpiredError()

        user_session = self._session_repository.get_by_id(self._session, session_id)
        if user_session is None or now > user_session.expires_at:
            logger.debug("refresh_failed reason=session_not_found_or_expired")
            raise SessionExpiredError()

        if user_session.revoked_at is not None:
            logger.debug("refresh_failed reason=session_already_revoked")
            raise SessionRevokedError()

        incoming_hash = hash_token(raw_token_secret)
        if not hmac.compare_digest(incoming_hash, user_session.refresh_token_hash):
            # REPLAY ATTACK: Revoke entire session chain
            logger.warning(
                "refresh_token_reuse_detected session_id=%s",
                session_id,
            )
            user_session.revoked_at = now
            self._session.commit()
            raise SessionRevokedError()

        # Normal Rotation: Issue new secret, update last_rotated_at
        new_raw_token_secret = secrets.token_urlsafe(32)
        new_hash = hash_token(new_raw_token_secret)

        user_session.refresh_token_hash = new_hash
        user_session.last_rotated_at = now
        if user_agent:
            user_session.user_agent = user_agent

        self._session.commit()

        # Build new tokens
        new_access_token = self.create_access_token(user_session.user_id)
        new_refresh_cookie = f"{session_id}.{new_raw_token_secret}"

        return new_access_token, new_refresh_cookie

    # --- Logout ---------------------------------------------------------------

    def logout(self, refresh_token_cookie: str | None) -> None:
        """Idempotently revoke the session corresponding to the refresh token."""
        now = self._clock()

        if not refresh_token_cookie or "." not in refresh_token_cookie:
            return

        try:
            session_id_str, raw_token_secret = refresh_token_cookie.split(".", 1)
            session_id = uuid.UUID(session_id_str)
        except ValueError:
            return

        user_session = self._session_repository.get_by_id(self._session, session_id)
        if user_session is None:
            return

        # Mirror refresh_session's secret check: a session_id with a
        # non-matching secret (forged/stale/already-rotated cookie) must not
        # revoke a session it doesn't actually authenticate.
        if hash_token(raw_token_secret) != user_session.refresh_token_hash:
            return

        if user_session.revoked_at is None:
            user_session.revoked_at = now
            self._session.commit()

    # --- Account Deletion (email-verified) ------------------------------------

    DELETE_TOKEN_TTL = timedelta(minutes=15)

    def request_account_deletion(self, user: User) -> None:
        """Generate a delete-confirmation token and email it to the user.

        The token is stored as a SHA-256 hash on the user row (no extra table).
        """
        now = self._clock()
        raw_token = secrets.token_urlsafe(MAGIC_LINK_TOKEN_BYTES)
        user.delete_token_hash = hash_token(raw_token)
        user.delete_token_expires_at = now + self.DELETE_TOKEN_TTL
        self._session.commit()

        confirm_url = f"{self._base_url}/auth/confirm-delete?token={raw_token}"
        try:
            self._email_sender.send_delete_confirmation(
                to_email=user.email,
                confirm_url=confirm_url,
                lang=user.preferred_language,
            )
        except EmailDeliveryError:
            logger.warning("delete_confirmation_email_send_failed")
            raise EmailServiceUnavailableError() from None

    def confirm_account_deletion(self, token: str) -> None:
        """Verify the delete token and soft-delete the user account.

        Revokes all sessions, soft-deletes food profiles, and marks the user as
        DISABLED with ``deleted_at`` set.
        """
        now = self._clock()
        token_hash = hash_token(token)

        user = self._user_repository.get_by_delete_token_hash(
            self._session, token_hash
        )

        if user is None or user.delete_token_expires_at is None:
            raise InvalidMagicLinkError()

        if now > user.delete_token_expires_at:
            user.delete_token_hash = None
            user.delete_token_expires_at = None
            self._session.commit()
            raise MagicLinkExpiredError()

        # 1. Soft-delete all food profiles
        for profile in self._food_profile_repository.list_by_user(
            self._session, user.id
        ):
            profile.deleted_at = now
            profile.is_default = False

        # 2. Revoke all sessions
        self._session_repository.revoke_all_for_user(
            self._session, user.id, now
        )

        # 3. Soft-delete user
        user.status = UserStatus.DISABLED
        user.deleted_at = now
        user.delete_token_hash = None
        user.delete_token_expires_at = None
        user.updated_at = now

        self._session.commit()

