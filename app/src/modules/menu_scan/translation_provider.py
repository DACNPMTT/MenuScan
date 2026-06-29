from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TranslationProviderError(Exception):
    """Base for translation provider errors."""


class TranslationTimeoutError(TranslationProviderError):
    """Provider exceeded timeout."""


class TranslationUnavailableError(TranslationProviderError):
    """Provider is temporarily unavailable."""


class TranslationProvider(Protocol):
    def translate_batch(
        self,
        *,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str | None]:
        """Translate a batch of texts. Return None for items that fail."""
        ...


@dataclass(frozen=True, slots=True)
class FakeTranslationProvider:
    """Returns '[EN] original' for vi->en, '[VI] original' for en->vi."""
    fail_with: str | None = None

    def translate_batch(
        self,
        *,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str | None]:
        if self.fail_with == "timeout":
            raise TranslationTimeoutError()
        if self.fail_with == "unavailable":
            raise TranslationUnavailableError()
        
        if self.fail_with == "partial":
            return [
                f"[{target_language.upper()}] {text}" if i % 2 == 1 else None
                for i, text in enumerate(texts)
            ]

        return [f"[{target_language.upper()}] {text}" for text in texts]
