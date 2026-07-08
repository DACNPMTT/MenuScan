import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UtensilsCrossed } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import {
  DietPreferencePicker,
  type DietPreferenceValue,
} from '@/features/menu-scan/components/DietPreferencePicker'

/** Optional post-registration step to capture allergies / dietary preferences.
 * Reached after set-password; always skippable and editable later in the profile. */
export function OnboardingPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('onboarding.docTitle')} | MenuScan`)
  const navigate = useNavigate()
  const { user, loading, updateProfile } = useAuth()

  const [value, setValue] = useState<DietPreferenceValue>(() => ({
    allergies: user?.allergies ?? [],
    dietary_preferences: user?.dietary_preferences ?? [],
  }))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && !user) navigate('/auth/login', { replace: true })
  }, [user, loading, navigate])

  const finish = () => navigate('/app', { replace: true })

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await updateProfile({
        allergies: value.allergies,
        dietary_preferences: value.dietary_preferences,
      })
      finish()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('onboarding.saveError'))
      setSaving(false)
    }
  }

  if (loading || !user) return null

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-5 py-[60px] font-sans">
      <div className="flex w-full max-w-[460px] flex-col">
        <header className="mb-8 flex flex-col items-center gap-4 text-center">
          <div className="flex size-16 items-center justify-center rounded-full bg-primary">
            <UtensilsCrossed className="size-8 text-white" aria-hidden />
          </div>
          <div className="flex flex-col gap-1.5">
            <h1 className="text-[24px] font-bold leading-[30px] text-primary-dark">
              {t('onboarding.title')}
            </h1>
            <p className="text-[15px] leading-[22px] text-ink-variant">
              {t('onboarding.subtitle')}
            </p>
          </div>
        </header>

        <div className="rounded-[12px] border border-hairline bg-canvas p-5">
          <DietPreferencePicker value={value} onChange={setValue} disabled={saving} />
        </div>

        {error && (
          <p role="alert" className="mt-3 text-[14px] text-destructive">
            {error}
          </p>
        )}

        <div className="mt-6 flex flex-col gap-3">
          <Button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="h-12 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
          >
            {saving ? t('onboarding.saving') : t('onboarding.save')}
          </Button>
          <button
            type="button"
            onClick={finish}
            disabled={saving}
            className="text-[15px] font-medium text-ink-variant transition-colors hover:text-primary-dark disabled:opacity-50"
          >
            {t('onboarding.skip')}
          </button>
        </div>
      </div>
    </div>
  )
}
