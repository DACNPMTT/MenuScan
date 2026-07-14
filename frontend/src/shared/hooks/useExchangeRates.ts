import { useEffect, useState } from 'react'
import { apiRequest } from '@/shared/lib/api'
import type { ExchangeRates } from '@/shared/lib/currency'

interface ExchangeRatesResponse {
  base: string
  rates: ExchangeRates
  updated_at: string | null
}

// Module-level cache so switching pages / re-mounting doesn't refetch the same
// base within a session (the backend also caches, this just avoids the request).
const cache = new Map<string, ExchangeRates>()

interface UseExchangeRatesResult {
  rates: ExchangeRates | null
  error: boolean
}

/** Fetches conversion rates for `base` from the backend, cached per base.
 * On failure `rates` stays null and callers fall back to the source currency.
 *
 * `enabled` gates the request. Pass false while the diner is still looking at the
 * menu's own prices: converting nothing needs no rates, and fetching them on every
 * page load spent a request on a conversion most diners never ask for. The fetch
 * fires the moment they actually pick a different currency. */
export function useExchangeRates(
  base: string,
  enabled: boolean = true,
): UseExchangeRatesResult {
  const normalizedBase = base.toUpperCase()
  // Fetched results tracked in state so a completed fetch re-renders; cached
  // bases are read during render — no synchronous setState inside the effect.
  const [fetched, setFetched] = useState<Record<string, ExchangeRates>>({})
  const [errored, setErrored] = useState<Record<string, boolean>>({})

  const rates = cache.get(normalizedBase) ?? fetched[normalizedBase] ?? null
  const error = Boolean(errored[normalizedBase])

  useEffect(() => {
    if (!enabled) return
    if (cache.has(normalizedBase)) return
    let active = true
    apiRequest<ExchangeRatesResponse>(
      `/api/v1/exchange-rates?base=${encodeURIComponent(normalizedBase)}`,
    )
      .then((res) => {
        cache.set(normalizedBase, res.rates)
        if (active) {
          setFetched((prev) => ({ ...prev, [normalizedBase]: res.rates }))
        }
      })
      .catch(() => {
        if (active) {
          setErrored((prev) => ({ ...prev, [normalizedBase]: true }))
        }
      })
    return () => {
      active = false
    }
  }, [enabled, normalizedBase])

  return { rates, error }
}
