import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  BadgeCheck,
  CalendarDays,
  KeyRound,
  Languages,
  Loader2,
  Mail,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Star,
  Trash2,
  UserCircle,
  UtensilsCrossed,
  X,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth, type FoodProfile, type User } from '@/app/providers/AuthProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { FoodProfilePreferencePicker } from '@/features/food-profile/components/FoodProfilePreferencePicker'
import {
  createEmptyFoodProfileDraft,
  foodProfileDraftToPreferences,
  labelPreferenceCode,
  profilePreferencesToDraft,
  type FoodProfilePreferenceDraft,
} from '@/features/food-profile/preferences'

const STATUS_STYLES: Record<string, string> = {
  ACTIVE: 'bg-[#e4f4df] text-[#256b2b]',
  LOCKED: 'bg-secondary text-ink-variant',
  DISABLED: 'bg-destructive/10 text-destructive',
}

function displayValue(value: string | null | undefined, fallback = 'Chưa thiết lập') {
  return value?.trim() ? value : fallback
}

const LOCALE_MAP: Record<string, string> = { vi: 'vi-VN', en: 'en-GB' }

function formatDate(value: string | undefined, lang: string) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const locale = LOCALE_MAP[lang] ?? 'en-GB'
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function initialsFrom(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1
    ? `${parts[0][0]}${parts[parts.length - 1][0]}`
    : name.slice(0, 2)
  return letters.toUpperCase()
}

export function ProfilePage() {
  const { t, i18n } = useTranslation()
  useDocumentTitle('Profile | MenuScan')
  const {
    user,
    accessToken,
    updateProfile,
    listFoodProfiles,
    createFoodProfile,
    updateFoodProfile,
    deleteFoodProfile,
  } = useAuth()
  const [fullProfile, setFullProfile] = useState<User | null>(null)
  const [foodProfiles, setFoodProfiles] = useState<FoodProfile[]>([])
  const [loading, setLoading] = useState(Boolean(accessToken))
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [draftDisplayName, setDraftDisplayName] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [profileEditorOpen, setProfileEditorOpen] = useState(false)
  const [editingFoodProfileId, setEditingFoodProfileId] = useState<string | null>(null)
  const [foodProfileName, setFoodProfileName] = useState('')
  const [foodProfileLanguage, setFoodProfileLanguage] = useState('vi')
  const [foodProfileDefault, setFoodProfileDefault] = useState(false)
  const [foodProfileDiet, setFoodProfileDiet] = useState<FoodProfilePreferenceDraft>(
    createEmptyFoodProfileDraft,
  )
  const [foodProfileSaving, setFoodProfileSaving] = useState(false)
  const [foodProfileError, setFoodProfileError] = useState<string | null>(null)

  const loadProfile = useCallback(async (mode: 'initial' | 'refresh') => {
    if (!accessToken) return
    if (mode === 'initial') setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const data = await apiRequest<User>('/api/v1/auth/me', {
        method: 'GET',
        token: accessToken,
      })
      const profiles = await listFoodProfiles()
      setFullProfile(data)
      setFoodProfiles(profiles)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t('profile.errors.loadFailed'),
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [accessToken, listFoodProfiles, t])

  useEffect(() => {
    void Promise.resolve().then(() => loadProfile('initial'))
  }, [loadProfile])

  const profile = fullProfile ?? user

  const displayName = useMemo(
    () => displayValue(profile?.display_name, profile?.email.split('@')[0] ?? t('profile.fallbackUser')),
    [profile?.display_name, profile?.email, t],
  )
  const initials = useMemo(() => initialsFrom(displayName), [displayName])
  const role = profile?.role
    ? t(`profile.roleLabels.${profile.role}`, { defaultValue: profile.role })
    : t('profile.notSet')
  const status = profile?.status ?? 'ACTIVE'
  const statusLabel = t(`profile.statusLabels.${status}`, { defaultValue: status })
  const statusStyle = STATUS_STYLES[status] ?? 'bg-secondary text-ink-variant'

  const startEditing = () => {
    setDraftDisplayName(profile?.display_name ?? '')
    setSaveError(null)
    setEditing(true)
  }

  const cancelEditing = () => {
    setSaveError(null)
    setEditing(false)
  }

  const handleSaveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saving) return
    const normalizedDisplayName = draftDisplayName.trim()
    if (normalizedDisplayName.length > 150) {
      setSaveError(t('profile.errors.nameTooLong'))
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await updateProfile({
        display_name: normalizedDisplayName || null,
      })
      setFullProfile(updated)
      setEditing(false)
    } catch (err) {
      setSaveError(
        err instanceof ApiError
          ? err.message
          : t('profile.errors.updateFailed'),
      )
    } finally {
      setSaving(false)
    }
  }

  const startAddFoodProfile = () => {
    setEditingFoodProfileId(null)
    setFoodProfileName(displayName)
    setFoodProfileLanguage(profile?.preferred_language ?? 'vi')
    setFoodProfileDefault(foodProfiles.length === 0)
    setFoodProfileDiet(createEmptyFoodProfileDraft())
    setFoodProfileError(null)
    setProfileEditorOpen(true)
  }

  const startEditFoodProfile = (foodProfile: FoodProfile) => {
    setEditingFoodProfileId(foodProfile.id)
    setFoodProfileName(foodProfile.display_name)
    setFoodProfileLanguage(foodProfile.preferred_language)
    setFoodProfileDefault(foodProfile.is_default)
    setFoodProfileDiet(profilePreferencesToDraft(foodProfile.preferences))
    setFoodProfileError(null)
    setProfileEditorOpen(true)
  }

  const closeFoodProfileEditor = () => {
    if (foodProfileSaving) return
    setProfileEditorOpen(false)
    setFoodProfileError(null)
  }

  const handleSaveFoodProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const normalizedName = foodProfileName.trim()
    if (!normalizedName) {
      setFoodProfileError(t('foodProfile.errors.nameRequired'))
      return
    }
    setFoodProfileSaving(true)
    setFoodProfileError(null)
    try {
      const payload = {
        display_name: normalizedName,
        preferred_language: foodProfileLanguage,
        is_default: foodProfileDefault || foodProfiles.length === 0,
        preferences: foodProfileDraftToPreferences(foodProfileDiet),
      }
      if (editingFoodProfileId) {
        await updateFoodProfile(editingFoodProfileId, payload)
      } else {
        await createFoodProfile(payload)
      }
      const profiles = await listFoodProfiles()
      setFoodProfiles(profiles)
      setProfileEditorOpen(false)
      if (payload.is_default && accessToken) {
        const data = await apiRequest<User>('/api/v1/auth/me', {
          method: 'GET',
          token: accessToken,
        })
        setFullProfile(data)
      }
    } catch (err) {
      setFoodProfileError(
        err instanceof ApiError
          ? err.message
          : t('foodProfile.errors.saveFailed'),
      )
    } finally {
      setFoodProfileSaving(false)
    }
  }

  const handleDeleteFoodProfile = async (foodProfile: FoodProfile) => {
    if (foodProfileSaving) return
    setFoodProfileSaving(true)
    setFoodProfileError(null)
    try {
      await deleteFoodProfile(foodProfile.id)
      const profiles = await listFoodProfiles()
      setFoodProfiles(profiles)
      if (accessToken) {
        const data = await apiRequest<User>('/api/v1/auth/me', {
          method: 'GET',
          token: accessToken,
        })
        setFullProfile(data)
      }
      if (editingFoodProfileId === foodProfile.id) {
        setProfileEditorOpen(false)
      }
    } catch (err) {
      setFoodProfileError(
        err instanceof ApiError
          ? err.message
          : t('foodProfile.errors.deleteFailed'),
      )
    } finally {
      setFoodProfileSaving(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-[13px] font-bold uppercase tracking-[0.7px] text-ink-variant">
            {t('profile.account')}
          </p>
          <h1 className="text-[32px] font-bold leading-[40px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
            {t('nav.profile')}
          </h1>
        </div>
        <button
          type="button"
          onClick={() => void loadProfile('refresh')}
          disabled={refreshing || loading}
          className="flex min-h-10 w-fit items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {refreshing ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <RefreshCw className="size-4" aria-hidden />
          )}
          {t('profile.refresh')}
        </button>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-5 flex items-start gap-3 rounded-[8px] border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{error}</span>
        </div>
      )}

      <section className="mt-[25px] rounded-[12px] border border-hairline bg-canvas p-5 sm:p-[30px]">
        {loading && !profile ? (
          <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 text-ink-variant">
            <Loader2 className="size-7 animate-spin text-primary-dark" aria-hidden />
            {t('profile.loading')}
          </div>
        ) : (
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-4">
              <div className="flex size-16 shrink-0 items-center justify-center rounded-[12px] bg-primary-dark text-[24px] font-bold text-white sm:size-20 sm:text-[30px]">
                {initials}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="truncate text-[24px] font-bold leading-[32px] text-ink sm:text-[30px] sm:leading-[36px]">
                    {displayName}
                  </h2>
                  <span className={`rounded-full px-3 py-1 text-[12px] font-bold ${statusStyle}`}>
                    {statusLabel}
                  </span>
                </div>
                <p className="mt-1 truncate text-[14px] text-ink-variant">
                  {profile?.email}
                </p>
              </div>
            </div>
            <Link
              to="/auth/set-password"
              className="flex min-h-10 w-full items-center justify-center gap-2 rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90 sm:w-fit"
            >
              <KeyRound className="size-4" aria-hidden />
              {t('profile.setPassword')}
            </Link>
          </div>
        )}
      </section>

      <div className="mt-[20px]">
        <form onSubmit={handleSaveProfile} noValidate className="rounded-[12px] border border-hairline bg-canvas">
          <header className="flex flex-col gap-3 border-b border-hairline bg-app-bg px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-[20px] leading-[28px] text-primary-dark">
                {t('profile.infoTitle')}
              </h2>
              {saveError && (
                <p role="alert" className="mt-1 text-[13px] text-destructive">
                  {saveError}
                </p>
              )}
            </div>
            {editing ? (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={cancelEditing}
                  disabled={saving}
                  className="flex min-h-10 items-center gap-2 rounded-[8px] border border-hairline bg-canvas px-4 py-2 text-[14px] font-bold text-ink-variant transition-colors hover:bg-surface-muted hover:text-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <X className="size-4" aria-hidden />
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex min-h-10 items-center gap-2 rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <Save className="size-4" aria-hidden />
                  )}
                  {t('common.save')}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={startEditing}
                className="flex min-h-10 w-fit items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10"
              >
                <Pencil className="size-4" aria-hidden />
                {t('common.edit')}
              </button>
            )}
          </header>
          <div className="grid grid-cols-1 divide-y divide-hairline sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            <div className="flex flex-col">
              {editing ? (
                <ProfileEditField
                  icon={<UserCircle className="size-5" />}
                  label={t('profile.displayName')}
                >
                  <input
                    type="text"
                    value={draftDisplayName}
                    onChange={(event) => setDraftDisplayName(event.target.value)}
                    maxLength={150}
                    placeholder={t('profile.enterDisplayName')}
                    disabled={saving}
                    className="h-10 w-full min-w-0 rounded-[8px] border border-hairline bg-canvas px-3 text-[15px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </ProfileEditField>
              ) : (
                <ProfileField
                  icon={<UserCircle className="size-5" />}
                  label={t('profile.displayName')}
                  value={displayValue(profile?.display_name, t('profile.notSet'))}
                />
              )}
              <ProfileField
                icon={<Mail className="size-5" />}
                label={t('profile.email')}
                value={displayValue(profile?.email, t('profile.noEmail'))}
              />
            </div>
            <div className="flex flex-col">
              <div className="flex min-h-[96px] gap-3 px-5 py-4">
                <span className="mt-1 flex size-5 shrink-0 text-[#5f6368]">
                  <Languages className="size-5" />
                </span>
                <div className="min-w-0">
                  <p className="mb-2 text-[13px] uppercase tracking-[0.5px] text-[#5f6368]">
                    {t('profile.interfaceLanguage')}
                  </p>
                  <LanguageSwitcher />
                </div>
              </div>
              <ProfileField
                icon={<ShieldCheck className="size-5" />}
                label={t('profile.role')}
                value={role}
              />
              <ProfileField
                icon={<BadgeCheck className="size-5" />}
                label={t('profile.statusLabel')}
                value={statusLabel}
              />
              <ProfileField
                icon={<CalendarDays className="size-5" />}
                label={t('profile.createdAt')}
                value={formatDate(profile?.created_at, i18n.language)}
              />
            </div>
          </div>
        </form>

        <section className="mt-[20px] rounded-[12px] border border-hairline bg-canvas">
          <header className="flex flex-col gap-3 border-b border-hairline bg-app-bg px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-[20px] leading-[28px] text-primary-dark">
                <UtensilsCrossed className="size-5" aria-hidden />
                {t('foodProfile.title')}
              </h2>
              <p className="mt-1 text-[14px] text-ink-variant">
                {t('foodProfile.subtitle')}
              </p>
              {foodProfileError && (
                <p role="alert" className="mt-2 text-[13px] text-destructive">
                  {foodProfileError}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={startAddFoodProfile}
              disabled={foodProfileSaving}
              className="flex min-h-10 w-fit items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Plus className="size-4" aria-hidden />
              {t('foodProfile.add')}
            </button>
          </header>

          <div className="flex flex-col divide-y divide-hairline">
            {foodProfiles.length ? (
              foodProfiles.map((foodProfile) => (
                <FoodProfileRow
                  key={foodProfile.id}
                  profile={foodProfile}
                  onEdit={() => startEditFoodProfile(foodProfile)}
                  onDelete={() => void handleDeleteFoodProfile(foodProfile)}
                  deleting={foodProfileSaving}
                />
              ))
            ) : (
              <div className="px-5 py-6 text-[14px] text-ink-variant">
                {t('foodProfile.empty')}
              </div>
            )}
          </div>

          {profileEditorOpen && (
            <form
              onSubmit={handleSaveFoodProfile}
              noValidate
              className="border-t border-hairline px-5 py-5"
            >
              <div className="grid gap-4 sm:grid-cols-[1fr_160px]">
                <label className="flex flex-col gap-2">
                  <span className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
                    {t('foodProfile.name')}
                  </span>
                  <input
                    type="text"
                    value={foodProfileName}
                    onChange={(event) => setFoodProfileName(event.target.value)}
                    maxLength={150}
                    disabled={foodProfileSaving}
                    className="h-10 w-full min-w-0 rounded-[8px] border border-hairline bg-canvas px-3 text-[15px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </label>
                <label className="flex flex-col gap-2">
                  <span className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
                    {t('foodProfile.language')}
                  </span>
                  <select
                    value={foodProfileLanguage}
                    onChange={(event) => setFoodProfileLanguage(event.target.value)}
                    disabled={foodProfileSaving}
                    className="h-10 rounded-[8px] border border-hairline bg-canvas px-3 text-[15px] text-ink outline-none transition-colors focus:border-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                  </select>
                </label>
              </div>

              <label className="mt-4 flex items-center gap-2 text-[14px] text-ink">
                <input
                  type="checkbox"
                  checked={foodProfileDefault}
                  onChange={(event) => setFoodProfileDefault(event.target.checked)}
                  disabled={foodProfileSaving || foodProfiles.length === 0}
                  className="size-4 accent-primary-dark"
                />
                {t('foodProfile.defaultProfile')}
              </label>

              <div className="mt-5">
                <FoodProfilePreferencePicker
                  value={foodProfileDiet}
                  onChange={setFoodProfileDiet}
                  disabled={foodProfileSaving}
                />
              </div>

              <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={closeFoodProfileEditor}
                  disabled={foodProfileSaving}
                  className="flex min-h-10 items-center justify-center gap-2 rounded-[8px] border border-hairline bg-canvas px-4 py-2 text-[14px] font-bold text-ink-variant transition-colors hover:bg-surface-muted hover:text-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <X className="size-4" aria-hidden />
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={foodProfileSaving}
                  className="flex min-h-10 items-center justify-center gap-2 rounded-[8px] bg-primary-dark px-4 py-2 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {foodProfileSaving ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <Save className="size-4" aria-hidden />
                  )}
                  {t('common.save')}
                </button>
              </div>
            </form>
          )}
        </section>
      </div>
    </div>
  )
}

function ProfileField({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex min-h-[96px] gap-3 px-5 py-4">
      <span className="mt-1 flex size-5 shrink-0 text-[#5f6368]">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="mb-1 text-[13px] uppercase tracking-[0.5px] text-[#5f6368]">
          {label}
        </p>
        <p className="break-words text-[16px] font-bold leading-[24px] text-ink">
          {value}
        </p>
      </div>
    </div>
  )
}

function ProfileEditField({
  children,
  icon,
  label,
}: {
  children: ReactNode
  icon: ReactNode
  label: string
}) {
  return (
    <div className="flex min-h-[96px] gap-3 px-5 py-4">
      <span className="mt-1 flex size-5 shrink-0 text-[#5f6368]">
        {icon}
      </span>
      <label className="min-w-0 flex-1">
        <span className="mb-2 block text-[13px] uppercase tracking-[0.5px] text-[#5f6368]">
          {label}
        </span>
        {children}
      </label>
    </div>
  )
}

function FoodProfileRow({
  profile,
  onEdit,
  onDelete,
  deleting,
}: {
  profile: FoodProfile
  onEdit: () => void
  onDelete: () => void
  deleting: boolean
}) {
  const { t } = useTranslation()
  const diet = profilePreferencesToDraft(profile.preferences)
  const formatCodes = (
    codes: string[],
    namespace: 'diet.allergens' | 'diet.preferences' | 'foodProfile.preferenceLabels',
  ) => (
    codes.length
      ? codes
        .map((code) => t(`${namespace}.${code}`, { defaultValue: labelPreferenceCode(code) }))
        .join(', ')
      : t('diet.none')
  )
  const allergies = formatCodes(diet.allergies, 'diet.allergens')
  const preferences = formatCodes(diet.dietary_preferences, 'diet.preferences')
  const likes = formatCodes(diet.likes, 'foodProfile.preferenceLabels')
  const avoids = formatCodes(diet.avoids, 'foodProfile.preferenceLabels')

  return (
    <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-[17px] font-bold text-ink">
            {profile.display_name}
          </h3>
          {profile.is_default && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary-dark px-2.5 py-1 text-[12px] font-bold text-white">
              <Star className="size-3" aria-hidden />
              {t('foodProfile.defaultBadge')}
            </span>
          )}
        </div>
        <div className="mt-2 flex flex-col gap-1 text-[14px] text-ink-variant">
          <p>
            <span className="font-bold">{t('diet.allergiesLabel')}:</span>{' '}
            {allergies}
          </p>
          <p>
            <span className="font-bold">{t('diet.preferencesLabel')}:</span>{' '}
            {preferences}
          </p>
          <p>
            <span className="font-bold">{t('foodProfile.sections.likes')}:</span>{' '}
            {likes}
          </p>
          <p>
            <span className="font-bold">{t('foodProfile.sections.avoids')}:</span>{' '}
            {avoids}
          </p>
        </div>
      </div>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={onEdit}
          disabled={deleting}
          className="flex size-10 items-center justify-center rounded-[8px] border border-hairline text-primary-dark transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={t('common.edit')}
        >
          <Pencil className="size-4" aria-hidden />
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="flex size-10 items-center justify-center rounded-[8px] border border-destructive/30 text-destructive transition-colors hover:bg-destructive/5 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={t('common.delete')}
        >
          <Trash2 className="size-4" aria-hidden />
        </button>
      </div>
    </div>
  )
}
