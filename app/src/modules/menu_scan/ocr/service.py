from __future__ import annotations

import re
from dataclasses import dataclass
from time import monotonic

from src.modules.menu_scan.ocr.document_preprocessor import DocumentPreprocessor
from src.modules.menu_scan.exceptions import (
    OcrEmptyResultError,
    OcrProcessingFailedError,
    OcrProviderUnavailableError,
    OcrTimeoutError,
    OcrUnsupportedDocumentError,
)
from src.modules.menu_scan.ocr_contract import OcrDocument
from src.modules.menu_scan.ocr.provider import (
    OcrProvider,
    ProviderProcessingError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\n]+")


@dataclass(frozen=True, slots=True)
class OcrSource:
    object_key: str
    data: bytes
    mime_type: str


@dataclass(frozen=True, slots=True)
class OcrService:
    preprocessor: DocumentPreprocessor
    provider: OcrProvider

    def process(self, source: OcrSource) -> OcrDocument:
        started_at = monotonic()
        try:
            prepared = self.preprocessor.prepare(
                data=source.data,
                mime_type=source.mime_type,
            )
            document = self.provider.extract_document(
                pages=prepared.pages,
                source_object_key=source.object_key,
            )
        except OcrUnsupportedDocumentError:
            raise
        except ProviderTimeoutError as error:
            raise OcrTimeoutError() from error
        except ProviderUnavailableError as error:
            raise OcrProviderUnavailableError() from error
        except ProviderProcessingError as error:
            raise OcrProcessingFailedError() from error
        except TimeoutError as error:
            raise OcrTimeoutError() from error
        except Exception as error:
            raise OcrProcessingFailedError() from error

        document = _normalized_document(
            document=document,
            processing_time_ms=max(
                document.processing_time_ms,
                int((monotonic() - started_at) * 1000),
            ),
            metadata={**prepared.metadata, **document.metadata},
        )
        if not document.text.strip():
            raise OcrEmptyResultError()
        return document


def _normalized_document(
    *,
    document: OcrDocument,
    processing_time_ms: int,
    metadata: dict[str, object],
) -> OcrDocument:
    pages = [
        page.model_copy(update={"text": _normalize_text(page.text)})
        for page in sorted(document.pages, key=lambda page: page.page_index)
    ]
    text = _normalize_text("\n\n".join(page.text for page in pages if page.text))
    if not text:
        text = _normalize_text(document.text)

    return document.model_copy(
        update={
            "text": text,
            "pages": pages,
            "processing_time_ms": processing_time_ms,
            "metadata": _safe_metadata(metadata),
        }
    )


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(
        _HORIZONTAL_WHITESPACE.sub(" ", line).strip()
        for line in normalized.split("\n")
    )
    return _MULTIPLE_BLANK_LINES.sub("\n\n", normalized).strip()


def _safe_metadata(metadata: dict[str, object]) -> dict[str, object]:
    blocked_fragments = ("key", "token", "secret", "authorization", "raw")
    safe: dict[str, object] = {}
    for key, value in metadata.items():
        normalized_key = key.lower()
        if any(fragment in normalized_key for fragment in blocked_fragments):
            continue
        if isinstance(value, str | int | float | bool) or value is None:
            safe[key] = value
    return safe
