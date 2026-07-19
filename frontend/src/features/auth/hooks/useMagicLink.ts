import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/shared/lib/api'
import { describeError } from '@/shared/lib/errors'
import type { MagicLinkResponse } from '@/features/auth/types'

export type MagicLinkState = 'idle' | 'loading' | 'success' | 'error'

const STATUS_OVERRIDES = {
  400: 'magicLink.invalidEmail',
  429: 'magicLink.rateLimited',
  503: 'magicLink.emailUnavailable',
} as const

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
      setErrorMessage(describeError(error, t, 'magicLink.generic', { statusOverrides: STATUS_OVERRIDES }))
      setState('error')
      return false
    }
  }

  return { state, errorMessage, resendAfterSeconds, request }
}
