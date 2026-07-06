import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { ApiError, api } from '@/shared/lib/api'
import type { MagicLinkResponse } from '@/features/auth/types'

export type MagicLinkState = 'idle' | 'loading' | 'success' | 'error'

function describeError(error: ApiError, t: TFunction): string {
  if (error.status === 429) return t('magicLink.rateLimited')
  if (error.status === 503) return t('magicLink.emailUnavailable')
  if (error.status === 400) return t('magicLink.invalidEmail')
  return t('magicLink.generic')
}

/**
 * Drives a magic-link request against `POST /auth/magic-links`. Owns only the
 * local request state (no global store); the page decides what to do on success.
 */
export function useMagicLink() {
  const { t } = useTranslation()
  const [state, setState] = useState<MagicLinkState>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [resendAfterSeconds, setResendAfterSeconds] = useState<number | null>(
    null,
  )

  async function request(email: string): Promise<boolean> {
    setState('loading')
    setErrorMessage(null)
    try {
      const data = await api<MagicLinkResponse>('/auth/magic-links', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setResendAfterSeconds(data.resend_after_seconds)
      setState('success')
      return true
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? describeError(error, t)
          : t('magicLink.generic'),
      )
      setState('error')
      return false
    }
  }

  return { state, errorMessage, resendAfterSeconds, request }
}
