from functools import lru_cache

from src.core.config import settings
from src.modules.exchange.service import ExchangeRateService


@lru_cache
def get_exchange_rate_service() -> ExchangeRateService:
    """Singleton so the in-process rate cache is shared across requests."""
    return ExchangeRateService(
        api_base_url=settings.exchange_rate_api_base_url,
        timeout_seconds=settings.exchange_rate_timeout_seconds,
        cache_ttl_seconds=settings.exchange_rate_cache_ttl_seconds,
    )
