import { useTranslation } from 'react-i18next'
import { MagicLinkForm } from '@/features/auth/components/MagicLinkForm'

export function RegisterPage() {
  const { t } = useTranslation()
  return (
    <MagicLinkForm
      heading={t('register.heading')}
      ctaLabel={t('auth.signUp')}
      alternate={{
        to: '/auth/login',
        prompt: t('auth.haveAccount'),
        label: t('auth.logIn'),
      }}
    />
  )
}
