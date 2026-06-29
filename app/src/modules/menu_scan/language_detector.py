from __future__ import annotations

import logging

from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

# Ensure deterministic results across calls.
DetectorFactory.seed = 0

# Sentinel value when detection fails.
UNKNOWN = "unknown"


def detect_language(text: str) -> str:
    """Detect the ISO 639-1 language code of *text*.

    Returns a two-letter language code (e.g. ``"vi"``, ``"en"``, ``"ja"``,
    ``"ko"``, ``"zh-cn"``, ``"th"`` …) or :data:`UNKNOWN` when the input is
    too short, purely numeric, or the library cannot determine the language.

    Uses Google's ``langdetect`` library which supports ~55 languages.
    """
    if not text or not text.strip():
        return UNKNOWN

    # langdetect needs a reasonable amount of text to be accurate.
    stripped = text.strip()
    if len(stripped) < 3:
        return UNKNOWN

    try:
        return detect(stripped)
    except LangDetectException:
        return UNKNOWN
