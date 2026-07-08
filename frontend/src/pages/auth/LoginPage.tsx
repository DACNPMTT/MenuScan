import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { MagicLinkForm } from '@/features/auth/components/MagicLinkForm'

interface LocationState {
  from?: {
    pathname: string
  }
}

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()

  useEffect(() => {
    if (!user) return
    const state = location.state as LocationState | null
    const origin = state?.from?.pathname || '/app'
    navigate(origin, { replace: true })
  }, [location.state, navigate, user])

  return (
    <MagicLinkForm
      heading={t('auth.logIn')}
      ctaLabel={t('auth.logIn')}
      alternate={{
        to: '/auth/register',
        prompt: t('auth.noAccount'),
        label: t('auth.signUp'),
      }}
    />
  )
}
