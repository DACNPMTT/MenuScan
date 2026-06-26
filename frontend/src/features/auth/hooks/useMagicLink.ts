import { useState } from 'react'
import { ApiError, api } from '@/shared/lib/api'
import type { MagicLinkResponse } from '@/features/auth/types'

export type MagicLinkState = 'idle' | 'loading' | 'success' | 'error'

function describeError(error: ApiError): string {
  if (error.status === 429) return 'Vui lòng đợi trước khi gửi lại yêu cầu.'
  if (error.status === 503) return 'Dịch vụ email tạm thời không khả dụng.'
  if (error.status === 400) return 'Email không hợp lệ.'
  return 'Đã có lỗi xảy ra. Vui lòng thử lại.'
}

/**
 * Drives a magic-link request against `POST /auth/magic-links`. Owns only the
 * local request state (no global store); the page decides what to do on success.
 */
export function useMagicLink() {
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
          ? describeError(error)
          : 'Đã có lỗi xảy ra. Vui lòng thử lại.',
      )
      setState('error')
      return false
    }
  }

  return { state, errorMessage, resendAfterSeconds, request }
}
