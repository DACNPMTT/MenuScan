"""Tests for the multi-tier menu-parser fallback chain wiring."""

from __future__ import annotations

from src.modules.menu_scan.dependencies import _FallbackMenuParser
from src.modules.menu_scan.llm_menu_parser import (
    LlmMenuParserTimeoutError,
    LlmMenuParserUnavailableError,
)
from src.modules.menu_scan.ocr_contract import ParsedMenuDraft


def _draft(provider: str) -> ParsedMenuDraft:
    return ParsedMenuDraft(
        parsing_provider=provider,
        target_language="en",
        items=[],
    )


class _StubParser:
    """Records calls; returns a draft tagged with its name, or raises."""

    def __init__(self, name: str, error: Exception | None = None) -> None:
        self.name = name
        self._error = error
        self.called = False

    def parse(
        self,
        document: object,
        *,
        target_language: str = "en",
        images: object = None,
        **kwargs,
    ) -> ParsedMenuDraft:
        self.called = True
        self.received_images = images
        if self._error is not None:
            raise self._error
        return _draft(self.name)


def test_fallback_uses_primary_when_it_succeeds() -> None:
    primary = _StubParser("primary")
    secondary = _StubParser("secondary")
    parser = _FallbackMenuParser(primary=primary, fallback=secondary)

    draft = parser.parse(object(), target_language="en")

    assert draft.parsing_provider == "primary"
    assert primary.called is True
    assert secondary.called is False


def test_fallback_switches_to_secondary_on_unavailable() -> None:
    primary = _StubParser("primary", error=LlmMenuParserUnavailableError("429"))
    secondary = _StubParser("secondary")
    parser = _FallbackMenuParser(primary=primary, fallback=secondary)

    draft = parser.parse(object(), target_language="en")

    assert draft.parsing_provider == "secondary"
    assert primary.called is True
    assert secondary.called is True


def test_nested_chain_flash_then_lite_then_rule_based() -> None:
    """Mirrors get_menu_parser wiring: flash → lite → rule-based."""
    flash = _StubParser("flash", error=LlmMenuParserUnavailableError("quota"))
    lite = _StubParser("lite", error=LlmMenuParserTimeoutError("timeout"))
    rule_based = _StubParser("rule_based")

    chain = _FallbackMenuParser(
        primary=flash,
        fallback=_FallbackMenuParser(primary=lite, fallback=rule_based),
    )

    draft = chain.parse(object(), target_language="en")

    assert draft.parsing_provider == "rule_based"
    assert flash.called is True
    assert lite.called is True
    assert rule_based.called is True


def test_nested_chain_stops_at_lite_when_it_succeeds() -> None:
    flash = _StubParser("flash", error=LlmMenuParserUnavailableError("quota"))
    lite = _StubParser("lite")
    rule_based = _StubParser("rule_based")

    chain = _FallbackMenuParser(
        primary=flash,
        fallback=_FallbackMenuParser(primary=lite, fallback=rule_based),
    )

    draft = chain.parse(object(), target_language="en")

    assert draft.parsing_provider == "lite"
    assert flash.called is True
    assert lite.called is True
    assert rule_based.called is False
