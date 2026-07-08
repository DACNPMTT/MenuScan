import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.modules.menu.models import Menu


class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_scan_sessions_user_id_users"),
        nullable=True,
    )
    source_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_page_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="1",
    )
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status"),
        nullable=False,
        server_default=ScanStatus.PENDING.value,
    )
    stage: Mapped[str | None] = mapped_column(String(30))
    progress: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="0",
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ocr_result: Mapped["OcrResult | None"] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    menu: Mapped["Menu | None"] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    source_files: Mapped[list["ScanSourceFile"]] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ScanSourceFile.sort_order",
    )

    __table_args__ = (
        CheckConstraint(
            "source_mime_type IN "
            "('image/jpeg', 'image/png', 'image/webp', 'application/pdf')",
            name="mime_type",
        ),
        CheckConstraint(
            "source_file_size BETWEEN 1 AND 10485760",
            name="file_size",
        ),
        CheckConstraint(
            "source_page_count BETWEEN 1 AND 8",
            name="page_count",
        ),
        CheckConstraint(
            "target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'",
            name="target_language",
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="progress"),
        CheckConstraint(
            "status != 'FAILED' OR error_code IS NOT NULL",
            name="failed_error_code",
        ),
        CheckConstraint(
            "status != 'COMPLETED' OR completed_at IS NOT NULL",
            name="completed_at",
        ),
        Index("ix_scan_sessions_user_id", user_id),
    )


class ScanSourceFile(Base):
    """One uploaded source file for a scan.

    A scan may carry several pages (multiple images uploaded together, or a
    multi-page PDF). ``scan_sessions.source_*`` holds the first/primary file for
    preview and history; this table holds every page in upload order so the
    pipeline can OCR them all and merge into one document.
    """

    __tablename__ = "scan_source_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scan_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "scan_sessions.id",
            name="fk_scan_source_files_scan_session_id_scan_sessions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="1",
    )
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan_session: Mapped[ScanSession] = relationship(back_populates="source_files")

    __table_args__ = (
        CheckConstraint(
            "mime_type IN "
            "('image/jpeg', 'image/png', 'image/webp', 'application/pdf')",
            name="source_file_mime_type",
        ),
        CheckConstraint(
            "file_size BETWEEN 1 AND 10485760",
            name="source_file_size",
        ),
        CheckConstraint("sort_order >= 0", name="source_file_sort_order"),
        Index("ix_scan_source_files_scan_session_id", scan_session_id),
    )


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scan_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "scan_sessions.id",
            name="fk_ocr_results_scan_session_id_scan_sessions",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_language: Mapped[str | None] = mapped_column(String(10))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    provider: Mapped[str | None] = mapped_column(String(50))
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan_session: Mapped[ScanSession] = relationship(back_populates="ocr_result")

    __table_args__ = (
        CheckConstraint(
            "confidence_score BETWEEN 0 AND 1",
            name="confidence",
        ),
        CheckConstraint(
            "processing_time_ms >= 0",
            name="processing_time",
        ),
    )
