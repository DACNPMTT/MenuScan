from __future__ import annotations

from io import BytesIO

import fitz
import pytest
from PIL import Image

from src.modules.menu_scan.ocr.document_preprocessor import DocumentPreprocessor
from src.modules.menu_scan.exceptions import (
    OcrEmptyResultError,
    OcrProcessingFailedError,
    OcrProviderUnavailableError,
    OcrTimeoutError,
    OcrUnsupportedDocumentError,
)
from src.modules.menu_scan.ocr.provider import FakeOcrProvider
from src.modules.menu_scan.ocr.service import OcrService, OcrSource


def _png_bytes(*, width: int = 640, height: int = 480) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color="white").save(output, format="PNG")
    return output.getvalue()


def _pdf_bytes(page_count: int) -> bytes:
    pdf = fitz.open()
    try:
        for index in range(page_count):
            page = pdf.new_page(width=300, height=200)
            page.insert_text((72, 72), f"Page {index + 1}")
        return pdf.tobytes()
    finally:
        pdf.close()


def _service(
    provider: FakeOcrProvider,
    *,
    max_image_dimension: int = 256,
) -> OcrService:
    return OcrService(
        preprocessor=DocumentPreprocessor(
            max_image_dimension=max_image_dimension,
            contrast_factor=1.0,
        ),
        provider=provider,
    )


def test_valid_image_is_preprocessed_and_converted_to_ocr_document() -> None:
    original = _png_bytes(width=1024, height=512)
    original_copy = bytes(original)
    service = _service(FakeOcrProvider(text_by_page=("Phở bò\n60.000đ",)))

    document = service.process(
        OcrSource(
            object_key="users/u/scans/s/source",
            data=original,
            mime_type="image/png",
        )
    )

    assert document.schema_version == "ocr-document.v1"
    assert document.provider == "fake"
    assert document.text == "Phở bò\n60.000đ"
    assert len(document.pages) == 1
    assert document.pages[0].page_index == 0
    assert document.pages[0].width <= 256
    assert original == original_copy


def test_pdf_pages_keep_original_order() -> None:
    service = _service(
        FakeOcrProvider(text_by_page=("Trang 1", "Trang 2", "Trang 3")),
    )

    document = service.process(
        OcrSource(
            object_key="users/u/scans/s/source",
            data=_pdf_bytes(3),
            mime_type="application/pdf",
        )
    )

    assert [page.page_index for page in document.pages] == [0, 1, 2]
    assert [page.text for page in document.pages] == ["Trang 1", "Trang 2", "Trang 3"]
    assert document.metadata["page_count"] == 3


def test_unsupported_document_maps_to_ocr_unsupported_document() -> None:
    service = _service(FakeOcrProvider())

    with pytest.raises(OcrUnsupportedDocumentError):
        service.process(
            OcrSource(
                object_key="users/u/scans/s/source",
                data=b"not an image",
                mime_type="text/plain",
            )
        )


def test_empty_provider_result_maps_to_ocr_empty_result() -> None:
    service = _service(FakeOcrProvider(text_by_page=("",)))

    with pytest.raises(OcrEmptyResultError):
        service.process(
            OcrSource(
                object_key="users/u/scans/s/source",
                data=_png_bytes(),
                mime_type="image/png",
            )
        )


def test_processing_time_is_recorded() -> None:
    service = _service(
        FakeOcrProvider(
            text_by_page=("Phá»Ÿ bÃ²\n60.000Ä‘",),
            processing_time_ms=123,
        )
    )

    document = service.process(
        OcrSource(
            object_key="users/u/scans/s/source",
            data=_png_bytes(),
            mime_type="image/png",
        )
    )

    assert document.processing_time_ms >= 123


def test_provider_timeout_maps_to_ocr_timeout() -> None:
    service = _service(FakeOcrProvider(fail_with="timeout"))

    with pytest.raises(OcrTimeoutError):
        service.process(
            OcrSource(
                object_key="users/u/scans/s/source",
                data=_png_bytes(),
                mime_type="image/png",
            )
        )


def test_provider_unavailable_maps_to_ocr_provider_unavailable() -> None:
    service = _service(FakeOcrProvider(fail_with="unavailable"))

    with pytest.raises(OcrProviderUnavailableError):
        service.process(
            OcrSource(
                object_key="users/u/scans/s/source",
                data=_png_bytes(),
                mime_type="image/png",
            )
        )


def test_provider_failure_maps_to_ocr_processing_failed() -> None:
    service = _service(FakeOcrProvider(fail_with="processing"))

    with pytest.raises(OcrProcessingFailedError):
        service.process(
            OcrSource(
                object_key="users/u/scans/s/source",
                data=_png_bytes(),
                mime_type="image/png",
            )
        )
