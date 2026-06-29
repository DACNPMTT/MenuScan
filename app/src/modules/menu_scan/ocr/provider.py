from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.modules.menu_scan.ocr.document_preprocessor import PreparedOcrPage
from src.modules.menu_scan.ocr_contract import (
    OcrBlock,
    OcrBoundingBox,
    OcrDocument,
    OcrLine,
    OcrPage,
)


class ProviderTimeoutError(Exception):
    """Provider exceeded the configured timeout budget."""


class ProviderUnavailableError(Exception):
    """Provider dependency is temporarily unavailable."""


class ProviderProcessingError(Exception):
    """Provider returned an unusable response or failed internally."""

    def __init__(
        self,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__("Provider returned an unusable response.")
        self.provider = provider
        self.status_code = status_code
        self.reason = reason


class OcrProvider(Protocol):
    def extract_document(
        self,
        *,
        pages: list[PreparedOcrPage],
        source_object_key: str,
    ) -> OcrDocument:
        """Return provider-neutral OCR output for preprocessed pages."""


@dataclass(frozen=True, slots=True)
class FakeOcrProvider:
    text_by_page: tuple[str, ...] = ("Fixture OCR text",)
    provider: str = "fake"
    provider_model: str = "fake-v1"
    confidence: float | None = 0.99
    processing_time_ms: int = 1
    fail_with: str | None = None

    def extract_document(
        self,
        *,
        pages: list[PreparedOcrPage],
        source_object_key: str,
    ) -> OcrDocument:
        if self.fail_with == "timeout":
            raise ProviderTimeoutError()
        if self.fail_with == "unavailable":
            raise ProviderUnavailableError()
        if self.fail_with == "processing":
            raise ProviderProcessingError()

        ocr_pages = [
            self._page_from_prepared(
                page=page,
                text=self.text_by_page[page.page_index]
                if page.page_index < len(self.text_by_page)
                else "",
            )
            for page in pages
        ]
        document_text = "\n\n".join(page.text for page in ocr_pages if page.text)

        return OcrDocument(
            provider=self.provider,
            provider_model=self.provider_model,
            source_object_key=source_object_key,
            text=document_text,
            confidence=self.confidence,
            pages=ocr_pages,
            processing_time_ms=self.processing_time_ms,
            metadata={"page_count": len(ocr_pages)},
        )

    def _page_from_prepared(
        self,
        *,
        page: PreparedOcrPage,
        text: str,
    ) -> OcrPage:
        blocks: list[OcrBlock] = []
        if text:
            bounding_box = OcrBoundingBox(
                left=0,
                top=0,
                width=1,
                height=1,
            )
            line = OcrLine(
                id=f"p{page.page_index}-l0",
                text=text,
                confidence=self.confidence,
                bounding_box=bounding_box,
            )
            blocks.append(
                OcrBlock(
                    id=f"p{page.page_index}-b0",
                    text=text,
                    confidence=self.confidence,
                    bounding_box=bounding_box,
                    lines=[line],
                    column_index=0,
                )
            )

        return OcrPage(
            page_index=page.page_index,
            width=page.width,
            height=page.height,
            text=text,
            confidence=self.confidence if text else None,
            blocks=blocks,
        )
