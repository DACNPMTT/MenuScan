/**
 * In-memory access-token manager with single-flight refresh.
 *
 * The access token lives in a module variable (never localStorage/sessionStorage),
 * so the refresh token — which is an httpOnly cookie — never reaches JS. The only
 * way to mint a fresh access token is `refreshAccessToken`, which calls the
 * refresh endpoint with the cookie via raw `fetch` (NOT `apiRequest`) so the
 * refresh call can never recurse into itself.
 *
 * Multi-tab coordination: a BroadcastChannel syncs the access token across
 * same-origin tabs. When one tab refreshes, every other tab adopts the new
 * token immediately, so a 401 in tab B is satisfied by the token tab A just
 * broadcast — without firing a second /auth/refresh. This avoids the classic
 * RTR race where two tabs refreshing at once trip reuse detection on the
 * backend and the whole session is revoked. (Backend has a 30s grace window as
 * a safety net regardless.)
 */
const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const PREFIX = import.meta.env.VITE_API_V1_PREFIX ?? '/api/v1'
const REFRESH_URL = `${BASE.replace(/\/$/, '')}${PREFIX}/auth/refresh`
const CHANNEL_NAME = 'menuscan-auth'
// How long to wait before retrying after a refresh that probably lost the
// cookie-rotation race against another tab. The browser stores the rotated
// cookie from the winning tab's response, so the retry uses the new cookie.
const CONCURRENT_REFRESH_BACKOFF_MS = 400

type AuthMessage =
  | { type: 'token'; token: string }
  | { type: 'cleared' }
  | { type: 'refreshing' }

const channel: BroadcastChannel | null =
  typeof BroadcastChannel !== 'undefined'
    ? new BroadcastChannel(CHANNEL_NAME)
    : null

if (channel) {
  channel.onmessage = (event: MessageEvent<AuthMessage>) => {
    const msg = event.data
    if (!msg) return
    if (msg.type === 'token' && typeof msg.token === 'string') {
      // Another tab refreshed — adopt its token without firing our own
      // /auth/refresh (avoids the cross-tab rotation race).
      accessToken = msg.token
    } else if (msg.type === 'cleared') {
      accessToken = null
    }
    // 'refreshing' is informational only; single-flight within this tab is
    // handled by the refreshPromise check below.
  }
}

function broadcast(msg: AuthMessage): void {
  channel?.postMessage(msg)
}

let accessToken: string | null = null
let refreshPromise: Promise<string | null> | null = null
let authFailureHandler: (() => void) | null = null

// localStorage key for the access_token. The token is also kept in-memory
// for synchronous reads; this mirror lets the session survive a full page
// reload (F5) without bouncing through /auth/refresh — the previous design
// lost the token on every navigation, which surfaced as a 5-min-feeling
// logout. The httpOnly refresh_token cookie remains the authoritative
// session bound; this is purely a UX cache that expires with the JWT.
const ACCESS_TOKEN_STORAGE_KEY = 'menuscan.access_token'

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
  } catch {
    // localStorage may be unavailable (private mode, quota, sandbox) — fall
    // back to pure in-memory behavior.
    return null
  }
}

function writeStoredToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
    else window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
  } catch {
    // Swallow — see readStoredToken.
  }
}

// Restore on module load so a page refresh doesn't blank the session.
accessToken = readStoredToken()

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
  writeStoredToken(token)
  if (token) broadcast({ type: 'token', token })
  else broadcast({ type: 'cleared' })
}

export function clearAccessToken(): void {
  accessToken = null
  writeStoredToken(null)
  broadcast({ type: 'cleared' })
}

export function setAuthFailureHandler(cb: (() => void) | null): void {
  authFailureHandler = cb
}

async function doRefreshOnce(): Promise<string> {
  // Raw fetch — NOT apiRequest — so the refresh call can never recurse.
  const res = await fetch(REFRESH_URL, { method: 'POST', credentials: 'include' })
  if (!res.ok) throw new Error(`refresh ${res.status}`)
  const body = (await res.json()) as { data?: { access_token?: unknown } }
  const token = body?.data?.access_token
  if (typeof token !== 'string') throw new Error('no access_token')
  accessToken = token
  broadcast({ type: 'token', token })
  return token
}

/**
 * Refresh the access token via the httpOnly `refresh_token` cookie.
 *
 * Single-flight: concurrent callers share the same in-flight refresh, so N
 * simultaneous 401s produce exactly one `POST /auth/refresh`. Cross-tab, the
 * BroadcastChannel means the winner broadcasts and the losers adopt its token
 * without calling /auth/refresh themselves.
 *
 * If the first attempt fails, we back off once and retry. The most common
 * cause of a single refresh 401 is a lost cookie-rotation race with another
 * tab — the backend returns 401 within its grace window WITHOUT revoking, the
 * browser has the rotated cookie by the time we retry, so the retry succeeds.
 * Only if both attempts fail do we clear auth state and run the failure
 * handler (logout).
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      broadcast({ type: 'refreshing' })
      try {
        return await doRefreshOnce()
      } catch (firstError) {
        await new Promise((r) => setTimeout(r, CONCURRENT_REFRESH_BACKOFF_MS))
        return await doRefreshOnce()
      }
    } catch {
      accessToken = null
      broadcast({ type: 'cleared' })
      authFailureHandler?.() // notifies AuthProvider to clear UI state
      return null
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}
