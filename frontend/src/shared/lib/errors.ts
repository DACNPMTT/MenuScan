import type { TFunction } from 'i18next'
import { ApiError } from './api'

export interface DescribeErrorOptions {
  /** Per-status i18n key overrides, e.g. { 401: 'auth.invalidCredentials' }. */
  statusOverrides?: Partial<Record<number, string>>
}

/**
 * Translate any thrown value into a user-facing localized string.
 *
 * Precedence:
 *  1. null/undefined                              -> t(fallbackKey)
 *  2. TypeError (fetch network failure)           -> t('errors.network')
 *  3. options.statusOverrides[error.status]       -> that key
 *  4. ApiError with backend-supplied message      -> backend message
 *  5. ApiError status mapped to a friendly key    -> that key
 *  6. fallback                                    -> t(fallbackKey)
 *
 * (4) honors api-response-template.md §Error: `message` is safe to display.
 * The marker for "no backend envelope was parsed" is `error.code === 'API_ERROR'`
 * — see api.ts: the unauthenticated fallback branch sets code to 'API_ERROR'
 * while both authenticated and unauthenticated success paths set a real code.
 */
export function describeError(
  error: unknown,
  t: TFunction,
  fallbackKey: string,
  options?: DescribeErrorOptions,
): string {
  if (error == null) return t(fallbackKey)
  if (error instanceof TypeError) return t('errors.network')

  if (error instanceof ApiError) {
    const override = options?.statusOverrides?.[error.status]
    if (override) return t(override)

    if (error.code !== 'API_ERROR' && error.message) return error.message

    if (error.status >= 500) return t('errors.serverError')
    const key = STATUS_KEY[error.status]
    return key ? t(key) : t(fallbackKey)
  }

  // Unknown Error/anything else: never leak .message.
  return t(fallbackKey)
}

const STATUS_KEY: Record<number, string> = {
  400: 'errors.badRequest',
  401: 'errors.sessionExpired',
  403: 'errors.forbidden',
  404: 'errors.notFound',
  408: 'errors.timeout',
  413: 'errors.fileTooLarge',
  415: 'errors.unsupportedType',
  422: 'errors.unprocessable',
  429: 'errors.rateLimited',
  504: 'errors.timeout',
}
