<<<<<<< HEAD
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
=======
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

interface RequestOptions extends RequestInit {
  token?: string
}

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
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

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {}
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
    credentials: 'include', // Important to send/receive HttpOnly refresh cookie
  })

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T
  }

  let body: ApiResponseEnvelope<T>
  try {
    body = await response.json() as ApiResponseEnvelope<T>
  } catch {
    throw new ApiError(
      response.status,
      'INVALID_JSON',
      'Phản hồi từ server không hợp lệ.'
    )
  }

  if (!response.ok || !body.success) {
    const errorDetails = body.error
    throw new ApiError(
      response.status,
      errorDetails?.code || 'UNKNOWN_ERROR',
      errorDetails?.message || 'Đã có lỗi xảy ra. Vui lòng thử lại.',
      errorDetails?.details
    )
  }

  return body.data as T
>>>>>>> 8e3ffc0ab76eefce856d544cf59b2eb07e49acca
}
