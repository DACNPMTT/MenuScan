import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { AuthShell } from '@/features/auth/components/AuthShell'
import { IconBadge } from '@/shared/components/IconBadge'

export function SetPasswordPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('setPassword.docTitle')} | MenuScan`)
  const navigate = useNavigate()
  const { user, loading, setPassword } = useAuth()

  const [password, setPasswordInput] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  // Protect route: redirect to login if not authenticated and not loading
  useEffect(() => {
    if (!loading && !user) {
      navigate('/auth/login', { replace: true })
    }
  }, [user, loading, navigate])

  const handleSetPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!password) {
      setPasswordError(t('setPassword.errors.enterPassword'))
      return
    }
    if (password.length < 6) {
      setPasswordError(t('setPassword.errors.minLength'))
      return
    }
    if (password !== confirmPassword) {
      setPasswordError(t('setPassword.errors.mismatch'))
      return
    }

    setSavingPassword(true)
    setPasswordError(null)
    try {
      await setPassword(password)
      // Offer the optional dietary-preferences onboarding step next.
      navigate('/auth/onboarding', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? err.message : t('setPassword.errors.saveFailed')
      setPasswordError(message)
    } finally {
      setSavingPassword(false)
    }
  }

  if (loading || !user) {
    return null // Will redirect in useEffect
  }

  return (
    <AuthShell>
      <div className="flex flex-col items-center gap-4 text-center">
        <IconBadge icon={Check} tone="success" size="lg" />
        <div className="flex flex-col gap-2">
          <h1 className="text-[22px] font-bold leading-tight text-ink">
            {t('setPassword.emailVerified')}
          </h1>
          <p className="max-w-[300px] text-[15px] leading-relaxed text-ink-variant">
            {t('setPassword.subtitle')}
          </p>
        </div>
      </div>

      <form onSubmit={handleSetPassword} noValidate className="flex flex-col gap-6 pb-2">
        <label className="flex flex-col gap-2">
          <span className="text-[14px] font-semibold text-ink">{t('setPassword.newPassword')}</span>
          <Input
            type="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPasswordInput(event.target.value)}
            placeholder={t('setPassword.minCharsPlaceholder')}
            aria-label={t('setPassword.newPassword')}
            disabled={savingPassword}
          />
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-[14px] font-semibold text-ink">{t('setPassword.confirmPassword')}</span>
          <Input
            type="password"
            required
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder={t('setPassword.reenterPlaceholder')}
            aria-label={t('setPassword.confirmPassword')}
            disabled={savingPassword}
          />
        </label>

        {passwordError && (
          <p role="alert" className="-mt-2 text-[14px] text-destructive">
            {passwordError}
          </p>
        )}

        <Button type="submit" size="lg" disabled={savingPassword}>
          {savingPassword ? t('setPassword.saving') : t('setPassword.save')}
        </Button>
      </form>
    </AuthShell>
  )
}
