/**
 * Batched interaction queue for the Discovery feed.
 *
 * Problem: the legacy FeedStack awaited `markSeen` / `saveRestaurant` on every
 * swipe, blocking the card advance on a network round-trip. Fast swiping
 * stacked in-flight requests and felt laggy.
 *
 * Solution: cards advance optimistically on swipe; the persistence requests
 * are queued here and flushed periodically, on threshold, or on lifecycle
 * events (visibilitychange / pagehide / unmount). The backend endpoints are
 * already idempotent (`ON CONFLICT DO NOTHING` for seen, 409 for duplicate
 * save, 204 for any DELETE), so retries and batched parallel fan-out are safe.
 *
 * The `apiDispatch` seam is injectable so the queue stays pure and testable;
 * `defaultApiDispatch` below is the production wiring.
 */
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '@/shared/lib/api'
import { getAccessToken } from '@/shared/lib/auth-token'
import { markSeen, saveRestaurant, unsaveRestaurant } from './api'

export type InteractionAction =
  | { kind: 'seen'; sourceId: number; action: 'skip' | 'view' }
  | { kind: 'save'; sourceId: number }
  | { kind: 'unsave'; sourceId: number }

export interface FlushResult {
  ok: number
  failed: number
}

export type ApiDispatch = (actions: InteractionAction[]) => Promise<FlushResult>

export interface InteractionQueueConfig {
  /** Once the queue reaches this size, a flush fires immediately. */
  flushThreshold: number
  /** How the batched actions are sent. Injectable for tests. */
  apiDispatch: ApiDispatch
  /** Fires with the count of failed actions after a flush (failed > 0). */
  onError?: (failedCount: number) => void
}

const DEFAULT_FLUSH_INTERVAL_MS = 2000
const DEFAULT_FLUSH_THRESHOLD = 5

/**
 * Dedupe key. Same `kind` + same `sourceId` collapses last-write-wins (so a
 * `seen=skip` followed by `seen=view` on one card only ships `view`). Different
 * `kind` on the same card (e.g. `seen=view` + `save`) both ship — they hit
 * distinct endpoints and the user's intent needs both.
 */
function compositeKey(a: InteractionAction): string {
  return `${a.kind}:${a.sourceId}`
}

export class InteractionQueue {
  private queue: InteractionAction[] = []
  private flushInFlight = false
  private readonly config: InteractionQueueConfig
  // Mutable so the hook can keep `onError` current without rebuilding the
  // queue (which would lose in-flight state).
  private onError: ((failedCount: number) => void) | undefined

  constructor(config: InteractionQueueConfig) {
    this.config = config
    this.onError = config.onError
  }

  /** Swap the error callback. Safe to call between flushes. */
  setOnError(cb: ((failedCount: number) => void) | undefined): void {
    this.onError = cb
  }

  enqueue(action: InteractionAction): void {
    this.queue.push(action)
    if (this.queue.length >= this.config.flushThreshold) {
      // Fire-and-forget: callers don't await enqueue.
      void this.flush()
    }
  }

  /**
   * Drain the queue and dispatch as one batch. Safe to call while a flush is
   * already in-flight — the in-flight flush owns its own snapshot, and any
   * concurrently enqueued actions stay queued for the next flush.
   */
  async flush(): Promise<FlushResult> {
    if (this.flushInFlight || this.queue.length === 0) {
      return { ok: 0, failed: 0 }
    }
    const batch = this.dedupe(this.queue.splice(0))
    this.flushInFlight = true
    try {
      const result = await this.config.apiDispatch(batch)
      if (result.failed > 0 && this.onError) this.onError(result.failed)
      return result
    } finally {
      this.flushInFlight = false
    }
  }

  /**
   * Best-effort fire-and-forget for `pagehide` / unmount / `visibilitychange`.
   * Each action goes out as its own `fetch(..., { keepalive: true })` so the
   * browser carries the request past page unload. No response handling — the
   * cards have already advanced optimistically and idempotency makes loss
   * acceptable.
   */
  flushSync(): void {
    if (this.queue.length === 0) return
    const batch = this.dedupe(this.queue.splice(0))
    for (const action of batch) {
      const req = buildKeepaliveRequest(action)
      if (req) void fetch(req.url, req.init)
    }
  }

  /** Drop pending actions without dispatching (used on hard logout). */
  clear(): void {
    this.queue = []
  }

  private dedupe(actions: InteractionAction[]): InteractionAction[] {
    const map = new Map<string, InteractionAction>()
    for (const a of actions) map.set(compositeKey(a), a)
    return [...map.values()]
  }
}

/**
 * Production dispatcher. Fans the batched actions out in parallel via the
 * existing typed API wrappers and tallies ok/failed via `Promise.allSettled`.
 *
 * `save` swallows `RESTAURANT_ALREADY_SAVED` (409): the user's intent — "this
 * is saved" — is already satisfied server-side, so it counts as success.
 */
export async function defaultApiDispatch(
  actions: InteractionAction[],
): Promise<FlushResult> {
  const results = await Promise.allSettled(actions.map(dispatchOne))
  return {
    ok: results.filter((r) => r.status === 'fulfilled').length,
    failed: results.filter((r) => r.status === 'rejected').length,
  }
}

async function dispatchOne(action: InteractionAction): Promise<unknown> {
  switch (action.kind) {
    case 'seen':
      return markSeen(action.sourceId, action.action)
    case 'save':
      return saveRestaurant(action.sourceId).catch((err) => {
        if (err instanceof ApiError && err.code === 'RESTAURANT_ALREADY_SAVED') return
        throw err
      })
    case 'unsave':
      return unsaveRestaurant(action.sourceId)
  }
}

/**
 * Build a `keepalive: true` fetch for `flushSync`. Bypasses `apiRequest`
 * (which is async + JSON-parsing) because pagehide gives us no time to await.
 * Auth header mirrors `apiRequest`: bearer token if present, cookies included.
 */
function buildKeepaliveRequest(
  action: InteractionAction,
): { url: string; init: RequestInit } | null {
  const base = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(
    /\/$/,
    '',
  )
  const prefix = import.meta.env.VITE_API_V1_PREFIX ?? '/api/v1'
  const token = getAccessToken()

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`

  const baseInit: RequestInit = {
    method: 'POST',
    headers,
    keepalive: true,
    credentials: 'include',
  }

  switch (action.kind) {
    case 'seen':
      return {
        url: `${base}${prefix}/feed/${action.sourceId}/seen`,
        init: { ...baseInit, body: JSON.stringify({ action: action.action }) },
      }
    case 'save':
      return {
        url: `${base}${prefix}/feed/saves/${action.sourceId}`,
        init: { ...baseInit, body: JSON.stringify({}) },
      }
    case 'unsave':
      return {
        url: `${base}${prefix}/feed/saves/${action.sourceId}`,
        init: { ...baseInit, method: 'DELETE' },
      }
  }
}

// ---------------------------------------------------------------------------
// React hook
// ---------------------------------------------------------------------------

export interface UseInteractionQueueOptions {
  flushIntervalMs?: number
  flushThreshold?: number
  apiDispatch?: ApiDispatch
  /** Fires with the count of actions that failed in a flush (failed > 0). */
  onError?: (failedCount: number) => void
}

export interface UseInteractionQueueResult {
  enqueue: (action: InteractionAction) => void
  flush: () => Promise<FlushResult>
}

/**
 * One queue per mounted FeedStack. Sets up the periodic flush timer plus the
 * lifecycle hooks (visibilitychange / pagehide / unmount) that drain the queue
 * via `keepalive` so no interactions are lost on navigation or refresh.
 */
export function useInteractionQueue(
  options: UseInteractionQueueOptions = {},
): UseInteractionQueueResult {
  const {
    flushIntervalMs = DEFAULT_FLUSH_INTERVAL_MS,
    flushThreshold = DEFAULT_FLUSH_THRESHOLD,
    apiDispatch = defaultApiDispatch,
    onError,
  } = options

  // One queue per mounted FeedStack. The lazy initializer pins the instance
  // for the component's lifetime; `flushThreshold` and `apiDispatch` are read
  // from the first render (stable defaults) so the queue's config never
  // silently changes mid-session.
  const [queue] = useState(
    () => new InteractionQueue({ flushThreshold, apiDispatch, onError }),
  )

  // Keep the queue's onError callback current without rebuilding the queue.
  useEffect(() => {
    queue.setOnError(onError)
  }, [queue, onError])

  const enqueue = useCallback((action: InteractionAction) => queue.enqueue(action), [queue])
  const flush = useCallback(() => queue.flush(), [queue])

  useEffect(() => {
    const interval = window.setInterval(() => void queue.flush(), flushIntervalMs)
    const onVisibility = () => {
      if (document.hidden) queue.flushSync()
    }
    const onPageHide = () => queue.flushSync()
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('pagehide', onPageHide)
    return () => {
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pagehide', onPageHide)
      // One last drain on unmount — covers SPA navigation away from /app/feed.
      queue.flushSync()
    }
  }, [queue, flushIntervalMs])

  return { enqueue, flush }
}
