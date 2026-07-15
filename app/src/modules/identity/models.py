import enum
import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    DISABLED = "DISABLED"


class PreferenceType(str, enum.Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    AVOID = "AVOID"
    ALLERGY = "ALLERGY"
    DIETARY_RULE = "DIETARY_RULE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(150))
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="vi",
    )
    # Dietary profile (optional). Codes come from the shared taxonomy; matched
    # against each dish's allergens / dietary_tags to warn or flag.
    allergies: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    dietary_preferences: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
        server_default=text("'{}'::text[]"),
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        server_default=UserRole.USER.value,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        nullable=False,
        server_default=UserStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Account deletion confirmation token (one-time, 15-minute TTL).
    delete_token_hash: Mapped[str | None] = mapped_column(String(255))
    delete_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    magic_link_tokens: Mapped[list["MagicLinkToken"]] = relationship(
        back_populates="user"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    food_profiles: Mapped[list["FoodProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "preferred_language IN ('vi', 'en')",
            name="preferred_language",
        ),
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_magic_link_tokens_user_id_users"),
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User | None] = relationship(back_populates="magic_link_tokens")

    __table_args__ = (
        Index(
            "ix_magic_link_tokens_email_created_at",
            email,
            created_at.desc(),
        ),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_user_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[IPv4Address | IPv6Address | None] = mapped_column(INET)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_rotated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (Index("ix_user_sessions_user_id", user_id),)


class FoodProfile(Base):
    __tablename__ = "food_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_food_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="food_profiles")
    preferences: Mapped[list["FoodProfilePreference"]] = relationship(
        back_populates="food_profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "preferred_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="preferred_language",
        ),
        Index("ix_food_profiles_user_id", user_id),
        Index(
            "uq_food_profiles_user_default",
            user_id,
            unique=True,
            postgresql_where=text("is_default = true AND deleted_at IS NULL"),
        ),
    )


class FoodProfilePreference(Base):
    __tablename__ = "food_profile_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    food_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "food_profiles.id",
            name="fk_food_profile_preferences_food_profile_id_food_profiles",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    preference_type: Mapped[PreferenceType] = mapped_column(
        Enum(PreferenceType, name="preference_type"),
        nullable=False,
    )
    intensity: Mapped[int | None] = mapped_column(SmallInteger)
    importance: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="3",
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    food_profile: Mapped[FoodProfile] = relationship(back_populates="preferences")

    __table_args__ = (
        UniqueConstraint(
            "food_profile_id",
            "code",
            "preference_type",
            name="uq_food_profile_preferences_profile_code_type",
        ),
        CheckConstraint("intensity BETWEEN 0 AND 5", name="intensity"),
        CheckConstraint("importance BETWEEN 1 AND 5", name="importance"),
        Index("ix_food_profile_preferences_food_profile_id", food_profile_id),
    )
