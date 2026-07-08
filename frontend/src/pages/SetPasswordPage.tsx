import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

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
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-5 py-[75px] font-sans">
      <div className="flex w-full max-w-[400px] flex-col">
        <header className="mb-[45px] flex flex-col items-center gap-[18px] text-center">
          <h1 className="text-[30px] font-bold leading-[34px] tracking-[-0.75px] text-primary-dark">
            MenuScan
          </h1>
          <div className="flex size-16 items-center justify-center rounded-full bg-primary">
            <Check className="size-8 text-white" aria-hidden />
          </div>
          <div className="flex flex-col gap-[7px]">
            <p className="text-[20px] leading-[30px] text-ink">
              {t('setPassword.emailVerified')}
            </p>
            <p className="text-[15px] leading-[22px] text-ink-variant">
              {t('setPassword.subtitle')}
            </p>
          </div>
        </header>

        <form onSubmit={handleSetPassword} noValidate className="flex flex-col gap-[30px] pb-4">
          <label className="flex flex-col gap-[5px]">
            <span className="text-[14px] leading-[14px] text-ink">{t('setPassword.newPassword')}</span>
            <Input
              type="password"
              required
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPasswordInput(event.target.value)}
              placeholder={t('setPassword.minCharsPlaceholder')}
              aria-label={t('setPassword.newPassword')}
              disabled={savingPassword}
              className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
            />
          </label>

          <label className="flex flex-col gap-[5px]">
            <span className="text-[14px] leading-[14px] text-ink">{t('setPassword.confirmPassword')}</span>
            <Input
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder={t('setPassword.reenterPlaceholder')}
              aria-label={t('setPassword.confirmPassword')}
              disabled={savingPassword}
              className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
            />
          </label>

          {passwordError && (
            <p role="alert" className="-mt-4 text-[14px] text-destructive">
              {passwordError}
            </p>
          )}

          <Button
            type="submit"
            disabled={savingPassword}
            className="h-12 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
          >
            {savingPassword ? t('setPassword.saving') : t('setPassword.save')}
          </Button>
        </form>
      </div>
    </div>
  )
}
