const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const PREFIX = import.meta.env.VITE_API_V1_PREFIX ?? '/api/v1'
const API_BASE_URL = BASE.replace(/\/$/, '')

interface RequestOptions extends RequestInit {
  token?: string
}

interface Envelope<T> {
  success: boolean
  data?: T
  error?: unknown
}

interface ApiResponseEnvelope<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly body?: unknown
  readonly code: string
  readonly details?: unknown

  constructor(status: number, body: unknown)
  constructor(status: number, code: string, message: string, details?: unknown)
  constructor(
    status: number,
    bodyOrCode: unknown,
    message?: string,
    details?: unknown,
  ) {
    if (typeof bodyOrCode === 'string') {
      super(message ?? bodyOrCode)
      this.code = bodyOrCode
      this.details = details
    } else {
      super(`API request failed with status ${status}`)
      this.body = bodyOrCode
      this.code = 'API_ERROR'
    }
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Fetch wrapper for endpoints under API_V1_PREFIX. The backend answers with
 * the `{ success, data } | { success, error }` envelope.
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

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { token, headers = {}, ...restOptions } = options

  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const url = `${API_BASE_URL}${cleanPath}`

  const requestHeaders = new Headers(headers)
  if (!requestHeaders.has('Content-Type') && !(restOptions.body instanceof FormData)) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  if (token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(url, {
    ...restOptions,
    headers: requestHeaders,
    credentials: 'include',
  })

  if (response.status === 204) {
    return {} as T
  }

  let body: ApiResponseEnvelope<T>
  try {
    body = (await response.json()) as ApiResponseEnvelope<T>
  } catch {
    throw new ApiError(
      response.status,
      'INVALID_JSON',
      'Server response is not valid JSON.',
    )
  }

  if (!response.ok || !body.success) {
    const errorDetails = body.error
    throw new ApiError(
      response.status,
      errorDetails?.code || 'UNKNOWN_ERROR',
      errorDetails?.message || 'Something went wrong. Please try again.',
      errorDetails?.details,
    )
  }

  return body.data as T
}
