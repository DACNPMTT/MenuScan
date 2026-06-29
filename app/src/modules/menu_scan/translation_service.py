from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from src.modules.menu_scan.language_detector import UNKNOWN, detect_language
from src.modules.menu_scan.ocr_contract import ParsedMenuDraft
from src.modules.menu_scan.translation_provider import (
    TranslationProvider,
    TranslationProviderError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TranslationService:
    provider: TranslationProvider
    detector: Callable[[str], str] = detect_language

    def translate_draft(self, draft: ParsedMenuDraft) -> ParsedMenuDraft:
        source_language = draft.source_language
        if not source_language:
            source_language = self._detect_source_language(draft)

        if not source_language or source_language == UNKNOWN:
            return self._update_draft_language(draft, source_language)

        if source_language.lower() == draft.target_language.lower():
            return self._update_draft_language(draft, source_language)

        texts_to_translate: list[str] = []
        # maps flattened index to (item_index, is_description)
        index_map: dict[int, tuple[int, bool]] = {}

        for i, item in enumerate(draft.items):
            if item.original_name:
                index_map[len(texts_to_translate)] = (i, False)
                texts_to_translate.append(item.original_name)

            if item.original_description:
                index_map[len(texts_to_translate)] = (i, True)
                texts_to_translate.append(item.original_description)

        if not texts_to_translate:
            return self._update_draft_language(draft, source_language)

        try:
            translated_texts = self.provider.translate_batch(
                texts=texts_to_translate,
                source_language=source_language,
                target_language=draft.target_language,
            )
        except TranslationProviderError as error:
            logger.warning(f"Translation failed: {error}")
            return self._update_draft_language(draft, source_language)

        new_items = list(draft.items)

        for flat_idx, translated in enumerate(translated_texts):
            if translated is None:
                continue

            if flat_idx not in index_map:
                continue

            item_index, is_description = index_map[flat_idx]
            current_item = new_items[item_index]

            update_dict = {}
            if is_description:
                update_dict["translated_description"] = translated
            else:
                update_dict["translated_name"] = translated

            new_items[item_index] = current_item.model_copy(update=update_dict)

        return draft.model_copy(
            update={
                "source_language": source_language,
                "items": new_items,
            }
        )

    def _detect_source_language(self, draft: ParsedMenuDraft) -> str | None:
        texts = []
        for item in draft.items:
            if item.original_name:
                texts.append(item.original_name)
            if item.original_description:
                texts.append(item.original_description)

        if not texts:
            return None

        combined_text = "\n".join(texts)
        detected = self.detector(combined_text)

        if detected == UNKNOWN:
            return None
        return detected

    def _update_draft_language(
        self, draft: ParsedMenuDraft, source_language: str | None
    ) -> ParsedMenuDraft:
        if draft.source_language == source_language:
            return draft
        return draft.model_copy(update={"source_language": source_language})
