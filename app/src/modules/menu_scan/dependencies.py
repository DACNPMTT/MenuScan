from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
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
from src.modules.menu_scan.repository import ScanSessionRepository
from src.modules.menu_scan.service import ScanService


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


def get_menu_parser() -> MenuParser:
    config = settings.llm
    if config.provider == "rule_based":
        return RuleBasedMenuParser()
    if config.provider == "gemini":
        assert config.api_key is not None  # noqa: S101
        return GeminiMenuParser(
            api_key=config.api_key,
            api_base_url=config.api_base_url,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER={config.provider!r}")
