/**
 * In-memory access-token manager with single-flight refresh.
 *
 * The access token lives in a module variable (never localStorage/sessionStorage),
 * so the refresh token — which is an httpOnly cookie — never reaches JS. The only
 * way to mint a fresh access token is `refreshAccessToken`, which calls the
 * refresh endpoint with the cookie via raw `fetch` (NOT `apiRequest`) so the
 * refresh call can never recurse into itself.
 */
const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const PREFIX = import.meta.env.VITE_API_V1_PREFIX ?? '/api/v1'
const REFRESH_URL = `${BASE.replace(/\/$/, '')}${PREFIX}/auth/refresh`

let accessToken: string | null = null
let refreshPromise: Promise<string | null> | null = null
let authFailureHandler: (() => void) | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = null
}

export function setAuthFailureHandler(cb: (() => void) | null): void {
  authFailureHandler = cb
}

/**
 * Refresh the access token via the httpOnly `refresh_token` cookie.
 *
 * Single-flight: concurrent callers share the same in-flight refresh, so N
 * simultaneous 401s produce exactly one `POST /auth/refresh`. Returns the new
 * token, or `null` when refresh fails (cookie missing/invalid/expired); on
 * failure the stored token is cleared and the registered failure handler runs.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      // Raw fetch — NOT apiRequest — so the refresh call can never recurse.
      const res = await fetch(REFRESH_URL, { method: 'POST', credentials: 'include' })
      if (!res.ok) throw new Error(`refresh ${res.status}`)
      const body = (await res.json()) as { data?: { access_token?: unknown } }
      const token = body?.data?.access_token
      if (typeof token !== 'string') throw new Error('no access_token')
      accessToken = token
      return token
    } catch {
      accessToken = null
      authFailureHandler?.() // notifies AuthProvider to clear UI state
      return null
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}
