from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import fitz
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

from src.modules.menu_scan.exceptions import OcrUnsupportedDocumentError

SUPPORTED_OCR_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_OCR_PAGES = 8
PDF_RENDER_DPI = 200


@dataclass(frozen=True, slots=True)
class PreparedOcrPage:
    page_index: int
    image_bytes: bytes
    mime_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class PreparedOcrDocument:
    pages: list[PreparedOcrPage]
    metadata: dict[str, int | str | float]


@dataclass(frozen=True, slots=True)
class DocumentPreprocessor:
    max_image_dimension: int = 2000
    contrast_factor: float = 1.1

    def prepare(
        self,
        *,
        data: bytes,
        mime_type: str,
    ) -> PreparedOcrDocument:
        if mime_type not in SUPPORTED_OCR_MIME_TYPES:
            raise OcrUnsupportedDocumentError()

        if mime_type == "application/pdf":
            return self._prepare_pdf(data)

        page = self._prepare_image_page(
            data=data,
            page_index=0,
        )
        return PreparedOcrDocument(
            pages=[page],
            metadata={
                "page_count": 1,
                "source_mime_type": mime_type,
                "max_image_dimension": self.max_image_dimension,
                "contrast_factor": self.contrast_factor,
            },
        )

    def _prepare_pdf(self, data: bytes) -> PreparedOcrDocument:
        try:
            pdf = fitz.open(stream=data, filetype="pdf")
        except Exception as error:
            raise OcrUnsupportedDocumentError() from error

        try:
            if pdf.needs_pass or len(pdf) == 0 or len(pdf) > MAX_OCR_PAGES:
                raise OcrUnsupportedDocumentError()

            pages = [
                self._prepare_image_page(
                    data=page.get_pixmap(dpi=PDF_RENDER_DPI).tobytes("png"),
                    page_index=page_index,
                )
                for page_index, page in enumerate(pdf)
            ]
            return PreparedOcrDocument(
                pages=pages,
                metadata={
                    "page_count": len(pages),
                    "source_mime_type": "application/pdf",
                    "pdf_render_dpi": PDF_RENDER_DPI,
                    "max_image_dimension": self.max_image_dimension,
                    "contrast_factor": self.contrast_factor,
                },
            )
        finally:
            pdf.close()

    def _prepare_image_page(
        self,
        *,
        data: bytes,
        page_index: int,
    ) -> PreparedOcrPage:
        try:
            with Image.open(BytesIO(data)) as image:
                processed = ImageOps.exif_transpose(image).convert("RGB")
        except (UnidentifiedImageError, OSError) as error:
            raise OcrUnsupportedDocumentError() from error

        processed.thumbnail(
            (self.max_image_dimension, self.max_image_dimension),
            Image.Resampling.LANCZOS,
        )
        if self.contrast_factor != 1:
            processed = ImageEnhance.Contrast(processed).enhance(self.contrast_factor)

        output = BytesIO()
        processed.save(output, format="PNG", optimize=True)
        width, height = processed.size

        return PreparedOcrPage(
            page_index=page_index,
            image_bytes=output.getvalue(),
            mime_type="image/png",
            width=width,
            height=height,
        )
