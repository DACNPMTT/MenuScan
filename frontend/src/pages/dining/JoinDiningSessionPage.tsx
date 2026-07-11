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
  Globe,
  User,
} from 'lucide-react'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
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
  target_language: string
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
  const [preferredLanguage, setPreferredLanguage] = useState('vi')
  const [value, setValue] = useState<FoodProfilePreferenceDraft>(() =>
    createEmptyFoodProfileDraft(),
  )

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [joined, setJoined] = useState(false)

  // Fetch session details on mount
  useEffect(() => {
    if (!inviteToken) {
      setSessionError(t('dining.invalidToken'))
      setLoadingSession(false)
      return
    }

    const fetchPublicSession = async () => {
      try {
        const data = await apiRequest<PublicSessionDetail>(
          `/api/v1/dining/public/sessions?invite_token=${inviteToken}`,
          { method: 'GET' },
        )
        setSession(data)
        setPreferredLanguage(data.target_language || 'vi')
      } catch (err) {
        setSessionError(
          err instanceof ApiError
            ? err.message
            : t('dining.sessionNotFound') || 'Invite session is not active.',
        )
      } finally {
        setLoadingSession(false)
      }
    }

    void fetchPublicSession()
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

  const handleSave = async () => {
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
      await apiRequest('/api/v1/dining/public/sessions/join', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          display_name: normalizedName,
          preferred_language: preferredLanguage,
          preferences: foodProfileDraftToPreferences(value),
        }),
        token: undefined, // Public call, no Bearer auth needed
      })
      // Query param token is needed by the backend
      // Wait, look at how the backend router handles the token!
      // In router.py:
      // @router.post("/public/sessions/join")
      // def join_session(payload: JoinDiningSessionRequest, invite_token: str = Query(...))
      // So invite_token is passed as a QUERY parameter in the URL: `/public/sessions/join?invite_token=xxx`!
      // But my call was just `/api/v1/dining/public/sessions/join`. I need to append the query param!
      // Yes: `/api/v1/dining/public/sessions/join?invite_token=${inviteToken}`
      // Let's rewrite the URL below!
    } catch (err) {
      // Catch blocks can handle this
    }
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
          preferred_language: preferredLanguage,
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
      <div className="flex min-h-dvh w-screen flex-col items-center justify-center bg-canvas">
        <Loader2 className="size-10 animate-spin text-primary-dark mb-2" />
        <p className="text-[15px] font-medium text-ink-variant">Đang kết nối tới phiên ăn...</p>
      </div>
    )
  }

  if (sessionError || !session) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-6 text-center font-sans">
        <div className="flex w-full max-w-[420px] flex-col items-center border border-hairline rounded-[16px] p-8 shadow-xs">
          <AlertCircle className="size-12 text-destructive mb-3" />
          <h1 className="text-[20px] font-bold text-primary-dark mb-2">Mã mời không khả dụng</h1>
          <p className="text-[14px] text-ink-variant mb-6">{sessionError}</p>
          <p className="text-[13px] text-ink-variant">
            Hãy liên hệ với Host bàn ăn của bạn để nhận mã QR hoặc liên kết mời mới.
          </p>
        </div>
      </div>
    )
  }

  if (joined) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-6 text-center font-sans">
        <div className="flex w-full max-w-[460px] flex-col items-center border border-hairline bg-canvas rounded-[20px] p-8 shadow-md">
          <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
            <CheckCircle2 className="size-10" />
          </div>
          <h1 className="text-[24px] font-bold text-primary-dark mb-2">{t('dining.joinSuccess')}</h1>
          <p className="text-[15px] text-ink-variant leading-relaxed mb-6">
            {t('dining.joinSuccessDesc')}
          </p>
          <div className="w-full bg-surface-muted rounded-[12px] p-4 text-left border border-hairline text-[13px] text-ink-variant flex flex-col gap-2">
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
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-5 py-[60px] font-sans">
      <div className="flex w-full max-w-[460px] flex-col">
        <header className="mb-8 flex flex-col items-center gap-4 text-center">
          <div className="flex size-16 items-center justify-center rounded-full bg-primary">
            <UtensilsCrossed className="size-8 text-white" aria-hidden />
          </div>
          <div className="flex flex-col gap-1.5">
            <h1 className="text-[24px] font-bold leading-[30px] text-primary-dark">
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
                index === step ? 'w-9 bg-primary-dark' : 'w-2.5 bg-hairline'
              }`}
            />
          ))}
        </div>

        {/* Stepper Card container */}
        <div className="overflow-hidden rounded-[12px] border border-hairline bg-canvas shadow-xs">
          <div
            className="flex transition-transform duration-300 ease-out"
            style={{ transform: `translateX(-${step * 100}%)` }}
          >
            {/* Step 1: User display name & language preference */}
            <section className="w-full shrink-0 p-5 flex flex-col gap-4">
              <h2 className="text-[18px] font-bold text-primary-dark">
                {t('onboarding.steps.profile')}
              </h2>
              <div className="flex flex-col gap-3">
                <label className="flex flex-col gap-1.5">
                  <span className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant flex items-center gap-1">
                    <User className="size-3.5" />
                    {t('dining.guestName')}
                  </span>
                  <Input
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder={t('dining.guestNamePlaceholder')}
                    maxLength={150}
                    disabled={saving}
                    className="h-11 rounded-[8px]"
                  />
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant flex items-center gap-1">
                    <Globe className="size-3.5" />
                    {t('dining.guestLanguage')}
                  </span>
                  <select
                    value={preferredLanguage}
                    onChange={(event) => setPreferredLanguage(event.target.value)}
                    disabled={saving}
                    className="h-11 rounded-[8px] border border-hairline bg-canvas px-3 text-[14px] text-primary-dark focus:outline-none focus:ring-1 focus:ring-primary-dark"
                  >
                    <option value="vi">Tiếng Việt (VI)</option>
                    <option value="en">English (EN)</option>
                  </select>
                </label>
              </div>
            </section>

            {/* Step 2: Allergies */}
            <section className="w-full shrink-0 p-5">
              <h2 className="mb-4 text-[18px] font-bold text-primary-dark">
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
              <h2 className="mb-4 text-[18px] font-bold text-primary-dark">
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
              <h2 className="mb-4 text-[18px] font-bold text-primary-dark">
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
              <h2 className="mb-4 text-[18px] font-bold text-primary-dark">
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
          <p role="alert" className="mt-3 text-[14px] text-destructive flex items-center gap-1.5">
            <AlertCircle className="size-4 shrink-0" />
            {error}
          </p>
        )}

        {/* Navigation actions */}
        <div className="mt-6 flex flex-col gap-3">
          <div className="flex gap-3">
            <Button
              type="button"
              onClick={goBack}
              disabled={saving || step === 0}
              variant="outline"
              className="h-12 flex-1 rounded-full"
            >
              <ChevronLeft className="size-4" aria-hidden />
              {t('common.back')}
            </Button>
            {step < steps.length - 1 ? (
              <Button
                type="button"
                onClick={goNext}
                disabled={saving}
                className="h-12 flex-1 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
              >
                {t('common.next')}
                <ChevronRight className="size-4" aria-hidden />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleJoinSession}
                disabled={saving}
                className="h-12 flex-1 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
              >
                {saving && <Loader2 className="size-4 animate-spin" aria-hidden />}
                {saving ? t('onboarding.saving') : t('onboarding.save')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
