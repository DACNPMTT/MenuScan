import { useEffect, useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  UtensilsCrossed,
  AlertCircle,
  CheckCircle2,
  User,
} from 'lucide-react'
import { Spinner } from '@/shared/components/Spinner'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card } from '@/shared/components/ui/card'
import { IconBadge } from '@/shared/components/IconBadge'
import { EmptyState } from '@/shared/components/EmptyState'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { FoodProfilePreferencePicker } from '@/features/food-profile/components/FoodProfilePreferencePicker'
import {
  createEmptyFoodProfileDraft,
  foodProfileDraftToPreferences,
  type FoodProfilePreferenceDraft,
} from '@/features/food-profile/preferences'

interface PublicSessionDetail {
  session_id: string
  mode: string
  status: string
  participant_count: number
  created_at: string
}

export function JoinDiningSessionPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('dining.joinTitle')} | MenuScan`)
  const [searchParams] = useSearchParams()
  const inviteToken = searchParams.get('token')

  // Public Session metadata
  const [session, setSession] = useState<PublicSessionDetail | null>(null)
  const [loadingSession, setLoadingSession] = useState(true)
  const [sessionError, setSessionError] = useState<string | null>(null)

  // Stepper flow state
  const [step, setStep] = useState(0)
  const [displayName, setDisplayName] = useState('')
  const [value, setValue] = useState<FoodProfilePreferenceDraft>(() =>
    createEmptyFoodProfileDraft(),
  )

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [joined, setJoined] = useState(false)

  // Fetch session details on mount
  useEffect(() => {
    if (!inviteToken) {
      Promise.resolve().then(() => {
        setSessionError(t('dining.invalidToken'))
        setLoadingSession(false)
      })
      return
    }

    let active = true
    const fetchPublicSession = async () => {
      try {
        const data = await apiRequest<PublicSessionDetail>(
          `/api/v1/dining/public/sessions?invite_token=${inviteToken}`,
          { method: 'GET' },
        )
        if (active) {
          setSession(data)
        }
      } catch (err) {
        if (active) {
          setSessionError(
            err instanceof ApiError
              ? err.message
              : t('dining.sessionNotFound') || 'Invite session is not active.',
          )
        }
      } finally {
        if (active) {
          setLoadingSession(false)
        }
      }
    }

    void fetchPublicSession()
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inviteToken])

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

  const goNext = () => {
    if (step === 0 && !displayName.trim()) {
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

  // Let's implement the correct handleSave with URL query param:
  const handleJoinSession = async () => {
    if (!inviteToken) return
    const normalizedName = displayName.trim()
    if (!normalizedName) {
      setError(t('onboarding.nameRequired'))
      setStep(0)
      return
    }

    setSaving(true)
    setError(null)

    try {
      await apiRequest(`/api/v1/dining/public/sessions/join?invite_token=${inviteToken}`, {
        method: 'POST',
        body: JSON.stringify({
          display_name: normalizedName,
          preferences: foodProfileDraftToPreferences(value),
        }),
      })
      setJoined(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('onboarding.saveError'))
    } finally {
      setSaving(false)
    }
  }

  if (loadingSession) {
    return (
      <PageTransition className="flex min-h-dvh w-screen flex-col items-center justify-center bg-app-bg">
        <Spinner label="Đang kết nối tới phiên ăn..." />
      </PageTransition>
    )
  }

  if (sessionError || !session) {
    return (
      <PageTransition className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-6 text-center">
        <EmptyState
          icon={AlertCircle}
          tone="destructive"
          title="Mã mời không khả dụng"
          description={
            <>
              <span className="block">{sessionError}</span>
              <span className="mt-2 block">
                Hãy liên hệ với Host bàn ăn của bạn để nhận mã QR hoặc liên kết mời mới.
              </span>
            </>
          }
        />
      </PageTransition>
    )
  }

  if (joined) {
    return (
      <PageTransition className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-6 text-center">
        <Card className="w-full max-w-[460px] items-center gap-5 rounded-3xl p-8 shadow-pop">
          <IconBadge icon={CheckCircle2} tone="success" size="lg" />
          <div className="flex flex-col gap-2">
            <h1 className="text-[24px] font-bold text-ink">{t('dining.joinSuccess')}</h1>
            <p className="text-[15px] leading-relaxed text-ink-variant">
              {t('dining.joinSuccessDesc')}
            </p>
          </div>
          <div className="flex w-full flex-col gap-2 rounded-2xl border border-border bg-panel p-4 text-left text-[13px] text-ink-variant">
            <div className="flex justify-between">
              <span>Tên hiển thị:</span>
              <span className="font-bold text-primary-dark">{displayName}</span>
            </div>
            <div className="flex justify-between">
              <span>Số sở thích đã gửi:</span>
              <span className="font-bold text-primary-dark">
                {foodProfileDraftToPreferences(value).length}
              </span>
            </div>
          </div>
        </Card>
      </PageTransition>
    )
  }

  return (
    <PageTransition className="flex min-h-dvh flex-col items-center justify-center bg-app-bg px-5 py-[60px]">
      <Card className="w-full max-w-[460px] gap-0 rounded-3xl px-8 py-10 shadow-pop">
        <header className="mb-8 flex flex-col items-center gap-4 text-center">
          <IconBadge icon={UtensilsCrossed} tone="primary" size="md" solid />
          <div className="flex flex-col gap-1.5">
            <h1 className="text-[24px] font-bold leading-[30px] text-ink">
              {t('dining.joinTitle')}
            </h1>
            <p className="text-[15px] leading-[22px] text-ink-variant">
              {t('dining.joinSubtitle')}
            </p>
          </div>
        </header>

        {/* Steps indicator dots */}
        <div className="mb-4 flex items-center justify-center gap-2">
          {steps.map((label, index) => (
            <button
              key={label}
              type="button"
              onClick={() => {
                if (index === 0 || displayName.trim()) {
                  setStep(index)
                }
              }}
              disabled={saving}
              aria-label={label}
              className={`h-2.5 rounded-full transition-all disabled:cursor-not-allowed ${
                index === step ? 'w-9 bg-primary' : 'w-2.5 bg-border'
              }`}
            />
          ))}
        </div>

        {/* Stepper Card container */}
        <div className="w-full overflow-hidden rounded-2xl border border-border bg-canvas shadow-1">
          <div
            className="flex transition-transform duration-300 ease-[var(--ease-out-quint)]"
            style={{ transform: `translateX(-${step * 100}%)` }}
          >
            {/* Step 1: User display name & language preference */}
            <section className="flex w-full shrink-0 flex-col gap-4 p-5">
              <h2 className="text-[18px] font-bold text-ink">
                {t('onboarding.steps.profile')}
              </h2>
              <div className="flex flex-col gap-3">
                <label className="flex flex-col gap-1.5">
                  <span className="flex items-center gap-1 text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
                    <User className="size-3.5" aria-hidden />
                    {t('dining.guestName')}
                  </span>
                  <Input
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder={t('dining.guestNamePlaceholder')}
                    maxLength={150}
                    disabled={saving}
                  />
                </label>
              </div>
            </section>

            {/* Step 2: Allergies */}
            <section className="w-full shrink-0 p-5">
              <h2 className="mb-4 text-[18px] font-bold text-ink">
                {t('onboarding.steps.allergies')}
              </h2>
              <FoodProfilePreferencePicker
                value={value}
                onChange={setValue}
                disabled={saving}
                sections={['allergies']}
              />
            </section>

            {/* Step 3: Diet preferences */}
            <section className="w-full shrink-0 p-5">
              <h2 className="mb-4 text-[18px] font-bold text-ink">
                {t('onboarding.steps.diet')}
              </h2>
              <FoodProfilePreferencePicker
                value={value}
                onChange={setValue}
                disabled={saving}
                sections={['dietary_preferences']}
              />
            </section>

            {/* Step 4: Likes */}
            <section className="w-full shrink-0 p-5">
              <h2 className="mb-4 text-[18px] font-bold text-ink">
                {t('onboarding.steps.likes')}
              </h2>
              <FoodProfilePreferencePicker
                value={value}
                onChange={setValue}
                disabled={saving}
                sections={['likes']}
              />
            </section>

            {/* Step 5: Avoids */}
            <section className="w-full shrink-0 p-5">
              <h2 className="mb-4 text-[18px] font-bold text-ink">
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

        {/* Error notification */}
        {error && (
          <p role="alert" className="mt-3 flex w-full items-center gap-1.5 text-[14px] text-destructive">
            <AlertCircle className="size-4 shrink-0" aria-hidden />
            {error}
          </p>
        )}

        {/* Navigation actions */}
        <div className="mt-6 flex w-full flex-col gap-3">
          <div className="flex gap-3">
            <Button
              type="button"
              onClick={goBack}
              disabled={saving || step === 0}
              variant="outline"
              size="lg"
              className="flex-1"
            >
              <ChevronLeft className="size-4" aria-hidden />
              {t('common.back')}
            </Button>
            {step < steps.length - 1 ? (
              <Button
                type="button"
                onClick={goNext}
                disabled={saving}
                size="lg"
                className="flex-1"
              >
                {t('common.next')}
                <ChevronRight className="size-4" aria-hidden />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleJoinSession}
                disabled={saving}
                size="lg"
                className="flex-1"
              >
                {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
                {saving ? t('onboarding.saving') : t('onboarding.save')}
              </Button>
            )}
          </div>
        </div>
      </Card>
    </PageTransition>
  )
}
