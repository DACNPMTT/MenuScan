from __future__ import annotations

from src.modules.menu_scan.ocr_contract import (
    OcrBlock,
    OcrBoundingBox,
    OcrDocument,
    OcrLine,
    OcrPage,
)


def make_single_column_document(
    lines: list[str],
    *,
    title: str | None = None,
) -> OcrDocument:
    page_lines = [title, *lines] if title else lines
    page = _make_page(page_index=0, columns=[page_lines])
    return _make_document(pages=[page])


def make_multi_column_document(
    lines_col0: list[str],
    lines_col1: list[str],
) -> OcrDocument:
    page = _make_page(page_index=0, columns=[lines_col0, lines_col1])
    return _make_document(pages=[page])


def make_multi_page_document(pages: list[list[str]]) -> OcrDocument:
    return _make_document(
        pages=[
            _make_page(page_index=page_index, columns=[lines])
            for page_index, lines in enumerate(pages)
        ]
    )


def _make_document(pages: list[OcrPage]) -> OcrDocument:
    text = "\n".join(page.text for page in pages)
    return OcrDocument(
        provider="fixture",
        provider_model="menu-parser-fixture",
        source_object_key="fixtures/menu-parser/source",
        detected_language="vi",
        text=text,
        confidence=0.92,
        pages=pages,
        processing_time_ms=1,
        metadata={"page_count": len(pages)},
    )


def _make_page(page_index: int, columns: list[list[str]]) -> OcrPage:
    blocks: list[OcrBlock] = []
    page_text_lines: list[str] = []
    for column_index, lines in enumerate(columns):
        left = 0.08 + (0.46 * column_index)
        width = 0.38 if len(columns) > 1 else 0.58
        for line_index, text in enumerate(lines):
            top = 0.06 + (line_index * 0.055)
            line_id = f"p{page_index}-c{column_index}-l{line_index}"
            block_id = f"p{page_index}-c{column_index}-b{line_index}"
            bounding_box = OcrBoundingBox(
                left=left,
                top=min(top, 0.95),
                width=width,
                height=0.04,
            )
            line = OcrLine(
                id=line_id,
                text=text,
                confidence=0.91,
                bounding_box=bounding_box,
            )
            blocks.append(
                OcrBlock(
                    id=block_id,
                    text=text,
                    confidence=0.91,
                    bounding_box=bounding_box,
                    lines=[line],
                    column_index=column_index,
                )
            )
            page_text_lines.append(text)

    return OcrPage(
        page_index=page_index,
        width=1200,
        height=1600,
        text="\n".join(page_text_lines),
        confidence=0.91,
        blocks=blocks,
    )
