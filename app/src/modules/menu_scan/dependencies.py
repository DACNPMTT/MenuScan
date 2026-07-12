import logging
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import SessionLocal, get_db
from src.modules.menu.repository import MenuRepository
from src.modules.menu_scan.adapters.gemini_translation import GeminiTranslationProvider
from src.modules.menu_scan.adapters.storage import (
    ObjectStorage,
    build_object_storage,
)
from src.modules.menu_scan.llm_menu_parser import GeminiMenuParser
from src.modules.menu_scan.menu_parser import MenuParser, RuleBasedMenuParser
from src.modules.menu_scan.ocr.adapters.google_vision import GoogleVisionOcrProvider
from src.modules.menu_scan.ocr.document_preprocessor import DocumentPreprocessor
from src.modules.menu_scan.ocr.provider import FakeOcrProvider, OcrProvider
from src.modules.menu_scan.ocr.service import OcrService
from src.modules.menu_scan.pipeline import ScanPipeline
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.service import ScanService
from src.modules.menu_scan.translation_provider import FakeTranslationProvider
from src.modules.menu_scan.translation_service import TranslationService

logger = logging.getLogger(__name__)


class _FallbackMenuParser:
    """Tries the primary parser; falls back to the rule-based parser on unavailability."""

    def __init__(self, primary: MenuParser, fallback: MenuParser) -> None:
        self._primary = primary
        self._fallback = fallback

    def parse(
        self,
        document: object,
        *,
        target_language: str = "en",
        images: object = None,
        preferences_data: list[dict[str, object]] | None = None,
        is_group: bool = False,
    ) -> object:
        from src.modules.menu_scan.llm_menu_parser import LlmMenuParserUnavailableError, LlmMenuParserTimeoutError
        try:
            return self._primary.parse(  # type: ignore[arg-type]
                document,  # type: ignore[arg-type]
                target_language=target_language,
                images=images,  # type: ignore[arg-type]
                preferences_data=preferences_data,
                is_group=is_group,
            )
        except (LlmMenuParserUnavailableError, LlmMenuParserTimeoutError) as exc:
            logger.warning(
                "menu_parser_primary_unavailable falling_back=rule_based reason=%s",
                exc,
            )
            return self._fallback.parse(  # type: ignore[arg-type]
                document,  # type: ignore[arg-type]
                target_language=target_language,
                images=images,  # type: ignore[arg-type]
                preferences_data=preferences_data,
                is_group=is_group,
            )


@lru_cache
def get_object_storage() -> ObjectStorage:
    return build_object_storage(settings.storage)


def get_scan_service(
    session: Session = Depends(get_db),
) -> ScanService:
    return ScanService(
        session=session,
        repository=ScanSessionRepository(),
        storage=get_object_storage(),
    )


def get_ocr_provider() -> OcrProvider:
    config = settings.ocr
    if config.provider == "fake":
        return FakeOcrProvider()
    if config.provider == "google_vision":
        assert config.google_vision_api_key is not None  # noqa: S101
        return GoogleVisionOcrProvider(
            api_key=config.google_vision_api_key,
            api_base_url=config.google_vision_api_base_url,
            timeout_seconds=config.timeout_seconds,
            feature_type=config.google_vision_model,
        )
    raise ValueError(f"Unsupported OCR_PROVIDER={config.provider!r}")


def get_ocr_service(
    provider: OcrProvider = Depends(get_ocr_provider),
) -> OcrService:
    return OcrService(
        preprocessor=DocumentPreprocessor(
            max_image_dimension=settings.ocr.max_image_dimension,
            contrast_factor=settings.ocr.contrast_factor,
        ),
        provider=provider,
    )


def _build_gemini_parser(model: str) -> GeminiMenuParser:
    config = settings.llm
    return GeminiMenuParser(
        api_key=config.api_key or "",
        api_keys=config.api_keys,
        api_base_url=config.api_base_url,
        model=model,
        timeout_seconds=config.timeout_seconds,
        prealign_csv=config.prealign_csv,
    )


def get_menu_parser() -> MenuParser:
    config = settings.llm
    if config.provider == "rule_based":
        return RuleBasedMenuParser()
    if config.provider == "gemini":
        # Failover chain built from the model list (strongest first). Each model
        # rotates the full key pool on 429/quota before the chain degrades to the
        # next model, and finally to the rule-based parser (no external
        # dependency). Each hop is taken only on Unavailable/Timeout.
        models = config.models or (config.model,)
        chain: MenuParser = RuleBasedMenuParser()
        for model in reversed(models):
            chain = _FallbackMenuParser(
                primary=_build_gemini_parser(model),
                fallback=chain,
            )
        return chain
    raise ValueError(f"Unsupported LLM_PROVIDER={config.provider!r}")


def get_translation_service() -> TranslationService:
    config = settings.llm
    if config.api_key:
        provider = GeminiTranslationProvider(
            api_key=config.api_key,
            api_keys=config.api_keys,
            api_base_url=config.api_base_url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
        )
    else:
        provider = FakeTranslationProvider()
    return TranslationService(provider=provider)


def get_scan_pipeline() -> ScanPipeline:
    # Only the Gemini parser consumes images; keep the rule-based path text-only.
    attach_images = settings.llm.multimodal and settings.llm.provider == "gemini"
    return ScanPipeline(
        session_factory=SessionLocal,
        storage=get_object_storage(),
        ocr_service=get_ocr_service(get_ocr_provider()),
        menu_parser=get_menu_parser(),
        translation_service=get_translation_service(),
        scan_repository=ScanSessionRepository(),
        menu_repository=MenuRepository(),
        attach_images=attach_images,
        image_max_dimension=settings.llm.image_max_dimension,
    )
