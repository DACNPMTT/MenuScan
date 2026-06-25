const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

interface RequestOptions extends RequestInit {
  token?: string
}

export class ApiError extends Error {
  status: number
  code: string
  details?: any

  constructor(status: number, code: string, message: string, details?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export async function apiRequest<T = any>(
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

  let body: any
  try {
    body = await response.json()
  } catch (e) {
    throw new ApiError(
      response.status,
      'INVALID_JSON',
      'Phản hồi từ server không hợp lệ.'
    )
  }

  if (!response.ok || !body.success) {
    const errorDetails = body.error || {}
    throw new ApiError(
      response.status,
      errorDetails.code || 'UNKNOWN_ERROR',
      errorDetails.message || 'Đã có lỗi xảy ra. Vui lòng thử lại.',
      errorDetails.details
    )
  }

  return body.data as T
}
