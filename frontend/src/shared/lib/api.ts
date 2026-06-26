const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const PREFIX = import.meta.env.VITE_API_V1_PREFIX ?? '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown
  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

interface Envelope<T> {
  success: boolean
  data?: T
  error?: unknown
}

/**
 * Fetch wrapper for the MenuScan API. The backend always answers with the
 * `{ success, data } | { success, error }` envelope; on any non-OK or
 * `success:false` response it throws `ApiError` carrying the status + raw body
 * so callers can map it to a user-facing message.
 */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${PREFIX}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })

  const json = (await response.json().catch(() => null)) as Envelope<T> | null

  if (!response.ok || !json?.success) {
    throw new ApiError(response.status, json)
  }

  return json.data as T
}
