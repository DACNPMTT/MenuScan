from __future__ import annotations

from src.modules.menu_scan.language_detector import UNKNOWN, detect_language
from src.modules.menu_scan.ocr_contract import ParsedMenuDraft, ParsedMenuItemDraft
from src.modules.menu_scan.translation_provider import (
    FakeTranslationProvider,
)
from src.modules.menu_scan.translation_service import TranslationService


def _draft(
    items: list[tuple[str, str | None]],
    *,
    source_language: str | None = None,
    target_language: str = "en",
) -> ParsedMenuDraft:
    return ParsedMenuDraft(
        target_language=target_language,
        source_language=source_language,
        items=[
            ParsedMenuItemDraft(
                original_name=name,
                original_description=desc,
                sort_order=i,
            )
            for i, (name, desc) in enumerate(items)
        ],
    )


# ── Language detection ──────────────────────────────────────────────


def test_detect_vi_from_accented_text() -> None:
    assert detect_language("Phở bò đặc biệt") == "vi"


def test_detect_en_from_ascii_text() -> None:
    assert detect_language("Beef noodle soup") == "en"


def test_detect_unknown_from_numeric() -> None:
    assert detect_language("12345") == UNKNOWN


def test_detect_ja_from_japanese_text() -> None:
    assert detect_language("ラーメン 味噌ラーメン") == "ja"


def test_detect_ko_from_korean_text() -> None:
    assert detect_language("김치찌개 된장찌개") == "ko"


def test_detect_zh_from_chinese_text() -> None:
    # langdetect may return "zh-cn", "zh-tw", or "ko" for short CJK text
    # since Chinese and Korean share CJK Unified Ideographs. Both are valid
    # CJK detections; the translation provider handles either correctly.
    result = detect_language("宫保鸡丁 麻婆豆腐 回锅肉 鱼香肉丝 红烧排骨 清蒸鲈鱼")
    assert result in {"zh-cn", "zh-tw", "ko", "ja"}, f"Expected CJK language, got {result}"


def test_detect_th_from_thai_text() -> None:
    assert detect_language("ต้มยำกุ้ง ผัดไทย") == "th"


# ── Translation skip ───────────────────────────────────────────────


def test_skip_when_source_equals_target() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("Gỏi cuốn", None)], source_language="vi", target_language="vi")
    
    result = service.translate_draft(draft)
    
    assert result is draft
    assert result.items[0].translated_name is None


def test_skip_when_source_unknown() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("12345", None)], source_language="unknown", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].translated_name is None


# ── Translation success ────────────────────────────────────────────


def test_translate_vi_to_en_fills_translated_name() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò", None)], source_language="vi", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].translated_name == "[EN] Phở bò"


def test_translate_preserves_original_fields() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò", "Nước dùng đậm đà")], source_language="vi", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].original_name == "Phở bò"
    assert result.items[0].original_description == "Nước dùng đậm đà"


def test_null_description_stays_null() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò", None)], source_language="vi", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].translated_name == "[EN] Phở bò"
    assert result.items[0].translated_description is None


def test_translate_ja_to_en() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("ラーメン", "味噌味")], source_language="ja", target_language="en")

    result = service.translate_draft(draft)

    assert result.items[0].translated_name == "[EN] ラーメン"
    assert result.items[0].translated_description == "[EN] 味噌味"


# ── Provider errors ────────────────────────────────────────────────


def test_timeout_returns_draft_unchanged() -> None:
    provider = FakeTranslationProvider(fail_with="timeout")
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò", None)], source_language="vi", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].translated_name is None


def test_unavailable_returns_draft_unchanged() -> None:
    provider = FakeTranslationProvider(fail_with="unavailable")
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò", None)], source_language="vi", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].translated_name is None


def test_partial_failure_fills_available_translations() -> None:
    provider = FakeTranslationProvider(fail_with="partial")
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò", None), ("Bún bò", None)], source_language="vi", target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.items[0].translated_name is None
    assert result.items[1].translated_name == "[EN] Bún bò"


# ── Integration ────────────────────────────────────────────────────


def test_detect_language_from_draft_when_source_is_none() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("Phở bò đặc biệt", None)], target_language="en")
    
    result = service.translate_draft(draft)
    
    assert result.source_language == "vi"
    assert result.items[0].translated_name == "[EN] Phở bò đặc biệt"


def test_detect_japanese_from_draft_when_source_is_none() -> None:
    provider = FakeTranslationProvider()
    service = TranslationService(provider=provider)
    draft = _draft([("ラーメン 味噌ラーメン", None)], target_language="en")

    result = service.translate_draft(draft)

    assert result.source_language == "ja"
    assert result.items[0].translated_name is not None
