import { useMemo, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Loader2, UtensilsCrossed } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { FoodProfilePreferencePicker } from '@/features/food-profile/components/FoodProfilePreferencePicker'
import { AuthShell } from '@/features/auth/components/AuthShell'
import { IconBadge } from '@/shared/components/IconBadge'
import {
  createEmptyFoodProfileDraft,
  foodProfileDraftToPreferences,
  type FoodProfilePreferenceDraft,
} from '@/features/food-profile/preferences'

/** Optional post-registration step to capture allergies / dietary preferences.
 * Reached after set-password; always skippable and editable later in the profile. */
export function OnboardingPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('onboarding.docTitle')} | MenuScan`)
  const navigate = useNavigate()
  const { user, loading, createFoodProfile } = useAuth()

  const [step, setStep] = useState(0)
  const [profileName, setProfileName] = useState<string | null>(null)
  const [value, setValue] = useState<FoodProfilePreferenceDraft>(() => ({
    ...createEmptyFoodProfileDraft(),
    allergies: user?.allergies ?? [],
    dietary_preferences: user?.dietary_preferences ?? [],
  }))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && !user) navigate('/auth/login', { replace: true })
  }, [user, loading, navigate])

  const steps = useMemo(
    () => [
      t('onboarding.steps.profile'),
      t('onboarding.steps.allergies'),
      t('onboarding.steps.diet'),
      t('onboarding.steps.likes'),
      t('onboarding.steps.avoids'),
    ],
    [t],
  )
  const defaultProfileName = useMemo(
    () => user?.display_name || user?.email.split('@')[0] || t('onboarding.defaultProfileName'),
    [t, user?.display_name, user?.email],
  )

  const finish = () => navigate('/app', { replace: true })

  const handleSave = async () => {
    if (!user) return
    const normalizedName = (profileName ?? defaultProfileName).trim()
    if (!normalizedName) {
      setError(t('onboarding.nameRequired'))
      setStep(0)
      return
    }
    setSaving(true)
    setError(null)
    try {
      await createFoodProfile({
        display_name: normalizedName,
        preferred_language: user.preferred_language || 'vi',
        is_default: true,
        preferences: foodProfileDraftToPreferences(value),
      })
      finish()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('onboarding.saveError'))
      setSaving(false)
    }
  }

  if (loading || !user) return null

  const goNext = () => {
    if (step === 0 && !(profileName ?? defaultProfileName).trim()) {
      setError(t('onboarding.nameRequired'))
      return
    }
    setError(null)
    setStep((current) => Math.min(current + 1, steps.length - 1))
  }

  const goBack = () => {
    setError(null)
    setStep((current) => Math.max(current - 1, 0))
  }

  return (
    <AuthShell maxWidth="max-w-[480px]">
      <div className="flex flex-col items-center gap-4 text-center">
        <IconBadge icon={UtensilsCrossed} tone="primary" size="lg" />
        <div className="flex flex-col gap-1.5">
          <h1 className="text-[24px] font-bold leading-tight tracking-tight text-ink">
            {t('onboarding.title')}
          </h1>
          <p className="max-w-[340px] text-[15px] leading-relaxed text-ink-variant">
            {t('onboarding.subtitle')}
          </p>
        </div>
      </div>

      {/* Step dots */}
      <div className="flex items-center justify-center gap-2">
        {steps.map((label, index) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(index)}
            disabled={saving}
            aria-label={label}
            className={`h-2.5 rounded-full transition-all disabled:cursor-not-allowed ${
              index === step ? 'w-9 bg-primary' : 'w-2.5 bg-border'
            }`}
          />
        ))}
      </div>

      {/* Stepper carousel */}
      <div className="overflow-hidden rounded-2xl border border-border bg-panel p-1">
        <div
          className="flex transition-transform duration-300 ease-out"
          style={{ transform: `translateX(-${step * 100}%)` }}
        >
          <section className="w-full shrink-0 p-4">
            <h2 className="text-[16px] font-bold text-primary">
              {t('onboarding.steps.profile')}
            </h2>
            <label className="mt-3 flex flex-col gap-2">
              <span className="text-[12px] font-bold uppercase tracking-wide text-ink-variant">
                {t('onboarding.profileName')}
              </span>
              <Input
                value={profileName ?? defaultProfileName}
                onChange={(event) => setProfileName(event.target.value)}
                maxLength={150}
                disabled={saving}
              />
            </label>
          </section>
          <section className="w-full shrink-0 p-4">
            <h2 className="mb-3 text-[16px] font-bold text-primary">
              {t('onboarding.steps.allergies')}
            </h2>
            <FoodProfilePreferencePicker
              value={value}
              onChange={setValue}
              disabled={saving}
              sections={['allergies']}
            />
          </section>
          <section className="w-full shrink-0 p-4">
            <h2 className="mb-3 text-[16px] font-bold text-primary">
              {t('onboarding.steps.diet')}
            </h2>
            <FoodProfilePreferencePicker
              value={value}
              onChange={setValue}
              disabled={saving}
              sections={['dietary_preferences']}
            />
          </section>
          <section className="w-full shrink-0 p-4">
            <h2 className="mb-3 text-[16px] font-bold text-primary">
              {t('onboarding.steps.likes')}
            </h2>
            <FoodProfilePreferencePicker
              value={value}
              onChange={setValue}
              disabled={saving}
              sections={['likes']}
            />
          </section>
          <section className="w-full shrink-0 p-4">
            <h2 className="mb-3 text-[16px] font-bold text-primary">
              {t('onboarding.steps.avoids')}
            </h2>
            <FoodProfilePreferencePicker
              value={value}
              onChange={setValue}
              disabled={saving}
              sections={['avoids']}
            />
          </section>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-[14px] text-destructive">
          {error}
        </p>
      )}

      <div className="flex flex-col gap-3">
        <div className="flex gap-3">
          <Button
            type="button"
            onClick={goBack}
            disabled={saving || step === 0}
            variant="outline"
            size="lg"
          >
            <ChevronLeft className="size-4" aria-hidden />
            {t('common.back')}
          </Button>
          {step < steps.length - 1 ? (
            <Button type="button" onClick={goNext} disabled={saving} size="lg">
              {t('common.next')}
              <ChevronRight className="size-4" aria-hidden />
            </Button>
          ) : (
            <Button type="button" onClick={handleSave} disabled={saving} size="lg">
              {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {saving ? t('onboarding.saving') : t('onboarding.save')}
            </Button>
          )}
        </div>
        <button
          type="button"
          onClick={finish}
          disabled={saving}
          className="text-[15px] font-medium text-ink-variant transition-colors hover:text-primary disabled:opacity-50"
        >
          {t('onboarding.skip')}
        </button>
      </div>
    </AuthShell>
  )
}
