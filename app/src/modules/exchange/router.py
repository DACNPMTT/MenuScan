from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status

from src.core.errors import DependencyUnavailableError
from src.core.responses import success_response
from src.modules.exchange.dependencies import get_exchange_rate_service
from src.modules.exchange.service import ExchangeRateError, ExchangeRateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("", status_code=status.HTTP_200_OK)
def get_exchange_rates(
    base: str = Query(default="VND", min_length=3, max_length=3),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
) -> dict[str, object]:
    """Return conversion rates keyed by currency code, relative to ``base``.

    Display-only: the frontend multiplies stored prices by these rates. Cached
    in-process for a TTL. Upstream failure maps to 503 so the client can fall
    back to showing the original currency.
    """
    try:
        rates = service.get_rates(base)
    except ExchangeRateError as error:
        logger.warning("exchange_rate_lookup_failed base=%s reason=%s", base, error)
        raise DependencyUnavailableError("exchange_rate") from error

    return success_response(
        data={
            "base": rates.base,
            "rates": rates.rates,
            "updated_at": rates.updated_at,
        }
    )
