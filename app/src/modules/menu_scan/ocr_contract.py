"""Provider-neutral OCR and parsed-menu contracts.

Dependency rule
---------------
OCR adapter  → produces  OcrDocument
Parser       → consumes  OcrDocument, produces ParsedMenuDraft
Worker       → calls     OcrAdapter.run(), passes OcrDocument to parser
Translation  → consumes  ParsedMenuDraft.items, writes translated_name /
               translated_description (or LLM parser populates them in one call)

No layer below the adapter boundary may import a provider SDK or raw response
type.  All provider-specific code lives in a single adapter module that
implements the OcrAdapter protocol defined at the bottom of this file.

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


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


class OcrAdapterError(Exception):
    """Raised by an OcrAdapter when OCR cannot be completed.

    Attributes
    ----------
    code:
        One of the OcrErrorCode values.  Worker maps this to the scan's
        error_code column.
    """

    def __init__(self, code: OcrErrorCode, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


class OcrAdapter:
    """Protocol every OCR provider adapter must satisfy.

    Adapters live in ``app/src/modules/menu_scan/adapters/<provider>.py``.
    They must not be imported by the parser, translation layer, or API
    routers — only by the scan worker.

    Contract
    --------
    * ``run()`` receives the raw file bytes and the MIME type declared by the
      upload validator.  The adapter is responsible for any format conversion
      (e.g. PDF → per-page images) before calling the provider.
    * On success, return a fully-populated ``OcrDocument``.
    * On recoverable provider failure, raise ``OcrAdapterError`` with the
      appropriate ``OcrErrorCode``.  The worker will catch this and transition
      the scan to FAILED.
    * Never persist, log, or return provider-specific raw responses, API keys,
      signed URLs, or any field listed in ``UNSAFE_PROVIDER_METADATA``.

    PDF handling
    ------------
    Adapters receive the raw PDF bytes.  The recommended strategy for MVP is:

    1. Convert each page to a PNG image using ``pymupdf`` (fitz) — no system
       dependency, pure-Python, no GCS bucket required.
    2. Call the provider's image endpoint once per page.
    3. Merge per-page results into a single ``OcrDocument`` with one
       ``OcrPage`` per converted page.

    This avoids the GCS-only restriction of ``files:annotate`` and keeps
    upload flow simple (bytes in → ``OcrDocument`` out).

    For providers that natively support multi-page PDF without GCS (e.g. a
    future self-hosted PaddleOCR), the adapter may skip conversion and use
    the provider's own PDF pipeline, as long as the ``OcrDocument`` output
    is identical in shape.

    Implementing a new adapter
    --------------------------
    1. Create ``adapters/<provider_code>.py``.
    2. Subclass or duck-type ``OcrAdapter``; implement ``run()``.
    3. Add ``provider_code`` as a string constant matching the ``provider``
       field written into ``OcrDocument``.
    4. Register the adapter in the worker's factory (not yet implemented —
       worker picks the adapter from ``settings.ocr.provider``).
    5. Add a fixture output file to ``doc/ocr-benchmark/fixtures/`` and run
       ``measure_provider_output.py`` against the ground truth before
       opening a PR.
    """

    #: Short provider code written to ``OcrDocument.provider``.
    provider_code: str

    def run(
        self,
        *,
        file_bytes: bytes,
        mime_type: str,
        source_object_key: str,
    ) -> OcrDocument:
        """Run OCR on ``file_bytes`` and return a normalized ``OcrDocument``.

        Parameters
        ----------
        file_bytes:
            Raw bytes of the uploaded file, as stored in object storage.
        mime_type:
            MIME type validated by the upload endpoint
            (``image/jpeg``, ``image/png``, ``application/pdf``).
        source_object_key:
            The object-storage key written to ``OcrDocument.source_object_key``
            for traceability.

        Raises
        ------
        OcrAdapterError
            When the provider cannot process the file.
        """
        raise NotImplementedError
