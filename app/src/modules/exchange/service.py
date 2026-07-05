"""Currency exchange-rate service.

Proxies a free upstream rate API (open.er-api.com by default) and caches the
result in-process for a TTL so the browser can do display-only currency
conversion without hitting the upstream on every request. No API key required.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


class ExchangeRateError(Exception):
    """Base error for exchange-rate retrieval failures."""


class ExchangeRateUnavailableError(ExchangeRateError):
    """Upstream rate provider failed or returned an unusable response."""


@dataclass(frozen=True, slots=True)
class ExchangeRates:
    base: str
    rates: dict[str, float]
    updated_at: str | None


@dataclass
class ExchangeRateService:
    api_base_url: str
    timeout_seconds: float
    cache_ttl_seconds: int
    client: httpx.Client | None = None
    _cache: dict[str, tuple[float, ExchangeRates]] = field(
        default_factory=dict, init=False, repr=False
    )
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def get_rates(self, base: str) -> ExchangeRates:
        """Return cached rates for ``base`` if fresh, otherwise fetch + cache."""
        base = base.upper()
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(base)
            if cached is not None and (now - cached[0]) < self.cache_ttl_seconds:
                return cached[1]

        rates = self._fetch(base)

        with self._lock:
            self._cache[base] = (time.monotonic(), rates)
        return rates

    def _fetch(self, base: str) -> ExchangeRates:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        try:
            response = client.get(f"{self.api_base_url}/latest/{base}")
        except httpx.HTTPError as error:
            raise ExchangeRateUnavailableError(
                "exchange rate provider request failed"
            ) from error
        finally:
            if owns_client:
                client.close()

        if response.status_code >= 400:
            raise ExchangeRateUnavailableError(
                f"exchange rate provider status={response.status_code}"
            )

        try:
            body = response.json()
        except ValueError as error:
            raise ExchangeRateUnavailableError(
                "exchange rate provider returned invalid json"
            ) from error

        if body.get("result") != "success":
            raise ExchangeRateUnavailableError(
                "exchange rate provider returned an error result"
            )

        raw_rates = body.get("rates") or {}
        rates = {
            str(code): float(value)
            for code, value in raw_rates.items()
            if isinstance(value, (int, float))
        }
        if not rates:
            raise ExchangeRateUnavailableError("exchange rate provider returned no rates")

        return ExchangeRates(
            base=str(body.get("base_code") or base),
            rates=rates,
            updated_at=body.get("time_last_update_utc"),
        )
