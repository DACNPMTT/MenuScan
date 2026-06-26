"""Provider-neutral OCR and parsed-menu contracts.

The OCR provider adapter maps proprietary responses into these DTOs. Parser and
translation code should only depend on this module, not on provider SDK shapes.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OcrErrorCode(StrEnum):
    UNSUPPORTED_INPUT = "UNSUPPORTED_INPUT"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    INVALID_DOCUMENT = "INVALID_DOCUMENT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_TEXT_FOUND = "NO_TEXT_FOUND"
    UNSAFE_PROVIDER_METADATA = "UNSAFE_PROVIDER_METADATA"


class OcrBoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    left: float = Field(ge=0, le=1)
    top: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class OcrSourceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_index: int = Field(ge=0)
    block_id: str | None = None
    line_id: str | None = None
    word_ids: list[str] = Field(default_factory=list)
    bounding_box: OcrBoundingBox | None = None


class OcrWord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: OcrBoundingBox


class OcrLine(BaseModel):
    """A logical line of text from OCR output.

    Maps to a Vision 'paragraph' or an Azure 'line'.  One OcrLine may
    correspond to multiple physical lines when the provider groups them
    as a single paragraph.  Adapters may split long paragraphs at
    detected line breaks.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: OcrBoundingBox
    words: list[OcrWord] = Field(default_factory=list)


class OcrBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: OcrBoundingBox
    lines: list[OcrLine] = Field(default_factory=list)
    column_index: int | None = Field(default=None, ge=0)


class OcrPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_index: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    unit: str = "pixel"
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    blocks: list[OcrBlock] = Field(default_factory=list)


class OcrDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "ocr-document.v1"
    provider: str
    provider_model: str | None = None
    source_object_key: str
    detected_language: str | None = None
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    pages: list[OcrPage]
    processing_time_ms: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedMenuItemDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_name: str
    original_description: str | None = None
    translated_name: str | None = None
    translated_description: str | None = None
    base_name: str | None = None
    variant_name: str | None = None
    variant_group: str | None = None
    price_text: str | None = None
    price: str | None = None
    currency: str | None = None
    category: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_references: list[OcrSourceReference] = Field(default_factory=list)
    sort_order: int = Field(ge=0)


class ParsedMenuDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "parsed-menu-draft.v1"
    parsing_provider: str | None = None
    title: str | None = None
    source_language: str | None = None
    target_language: str
    default_currency: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_document: OcrSourceReference | None = None
    items: list[ParsedMenuItemDraft]
    warnings: list[OcrErrorCode] = Field(default_factory=list)
