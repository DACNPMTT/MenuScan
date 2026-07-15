import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  BadgeCheck,
  CalendarDays,
  CheckCircle2,
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
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Input } from '@/shared/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select'
import { SectionCard } from '@/shared/components/SectionCard'
import { IconBadge } from '@/shared/components/IconBadge'
import { Spinner } from '@/shared/components/Spinner'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Reveal } from '@/shared/components/motion/Reveal'
import { AnimatePresence, motion } from 'motion/react'

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
    requestDeleteAccount,
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

  // Delete Account State
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteDialogStep, setDeleteDialogStep] = useState<1 | 2>(1)
  const [deleteEmailInput, setDeleteEmailInput] = useState('')
  const [deleteRequesting, setDeleteRequesting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleteSuccessMsg, setDeleteSuccessMsg] = useState<string | null>(null)

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
  const statusVariant: 'success' | 'secondary' | 'destructive' =
    status === 'ACTIVE' ? 'success' : status === 'DISABLED' ? 'destructive' : 'secondary'

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

  const handleRequestDelete = async (e: FormEvent) => {
    e.preventDefault()
    if (deleteEmailInput !== profile?.email) {
      setDeleteError(t('deleteAccount.errors.emailMismatch'))
      return
    }
    setDeleteRequesting(true)
    setDeleteError(null)
    setDeleteSuccessMsg(null)
    try {
      const res = await requestDeleteAccount()
      setDeleteSuccessMsg(res.message)
      setDeleteEmailInput('')
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : t('deleteAccount.errors.requestFailed'),
      )
    } finally {
      setDeleteRequesting(false)
    }
  }

  return (
    <PageTransition>
      <div className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
        <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col gap-2">
            <p className="text-[13px] font-bold uppercase tracking-[0.7px] text-ink-variant">
              {t('profile.account')}
            </p>
            <h1 className="text-[32px] font-bold leading-[40px] text-ink sm:text-[44px] sm:leading-[52px]">
              {t('nav.profile')}
            </h1>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => void loadProfile('refresh')}
            disabled={refreshing || loading}
          >
            {refreshing ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-4" aria-hidden />
            )}
            {t('profile.refresh')}
          </Button>
        </header>

        {error && (
          <div
            role="alert"
            className="mt-5 flex items-start gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-[14px] text-destructive"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        )}

        <Reveal className="mt-[25px]">
          <SectionCard>
            {loading && !profile ? (
              <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 text-ink-variant">
                <Spinner label={t('profile.loading')} />
                <span aria-hidden className="text-[14px]">
                  {t('profile.loading')}
                </span>
              </div>
            ) : (
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex min-w-0 items-center gap-4">
                  <div className="flex size-16 shrink-0 items-center justify-center rounded-2xl bg-primary text-[24px] font-bold text-white shadow-2 shadow-primary/30 sm:size-20 sm:text-[30px]">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="truncate text-[24px] font-bold leading-[32px] text-ink sm:text-[30px] sm:leading-[36px]">
                        {displayName}
                      </h2>
                      <Badge variant={statusVariant}>{statusLabel}</Badge>
                    </div>
                    <p className="mt-1 truncate text-[14px] text-ink-variant">
                      {profile?.email}
                    </p>
                  </div>
                </div>
                <Button asChild className="w-full sm:w-fit">
                  <Link to="/auth/set-password">
                    <KeyRound className="size-4" aria-hidden />
                    {t('profile.setPassword')}
                  </Link>
                </Button>
              </div>
            )}
          </SectionCard>
        </Reveal>

        <Reveal delay={0.08} className="mt-[20px]">
          <form onSubmit={handleSaveProfile} noValidate>
            <SectionCard
              flush
              title={
                <span className="flex flex-col gap-1">
                  <span className="flex items-center gap-2">
                    <IconBadge icon={UserCircle} size="sm" />
                    {t('profile.infoTitle')}
                  </span>
                  {saveError && (
                    <span role="alert" className="text-[13px] font-normal text-destructive">
                      {saveError}
                    </span>
                  )}
                </span>
              }
              action={
                editing ? (
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={cancelEditing}
                      disabled={saving}
                    >
                      <X className="size-4" aria-hidden />
                      {t('common.cancel')}
                    </Button>
                    <Button type="submit" disabled={saving}>
                      {saving ? (
                        <Loader2 className="size-4 animate-spin" aria-hidden />
                      ) : (
                        <Save className="size-4" aria-hidden />
                      )}
                      {t('common.save')}
                    </Button>
                  </div>
                ) : (
                  <Button type="button" variant="outline" onClick={startEditing}>
                    <Pencil className="size-4" aria-hidden />
                    {t('common.edit')}
                  </Button>
                )
              }
              bodyClassName="grid grid-cols-1 divide-y divide-border sm:grid-cols-2 sm:divide-x sm:divide-y-0"
            >
              <div className="flex flex-col">
                {editing ? (
                  <ProfileEditField
                    icon={<UserCircle className="size-5" />}
                    label={t('profile.displayName')}
                  >
                    <Input
                      type="text"
                      value={draftDisplayName}
                      onChange={(event) => setDraftDisplayName(event.target.value)}
                      maxLength={150}
                      placeholder={t('profile.enterDisplayName')}
                      disabled={saving}
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
                <div className="flex min-h-[96px] gap-3 px-6 py-4">
                  <span className="mt-1 flex size-5 shrink-0 text-ink-variant">
                    <Languages className="size-5" />
                  </span>
                  <div className="min-w-0">
                    <p className="mb-2 text-[13px] uppercase tracking-[0.5px] text-ink-variant">
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
            </SectionCard>
          </form>
        </Reveal>

        <Reveal delay={0.16} className="mt-[20px]">
          <SectionCard
            flush
            title={
              <span className="flex items-center gap-2">
                <IconBadge icon={UtensilsCrossed} size="sm" />
                {t('foodProfile.title')}
              </span>
            }
            description={t('foodProfile.subtitle')}
            action={
              <Button
                type="button"
                variant="outline"
                onClick={startAddFoodProfile}
                disabled={foodProfileSaving}
              >
                <Plus className="size-4" aria-hidden />
                {t('foodProfile.add')}
              </Button>
            }
          >
            {foodProfileError && (
              <div className="px-6 pt-4">
                <p role="alert" className="text-[13px] text-destructive">
                  {foodProfileError}
                </p>
              </div>
            )}

            <div className="flex flex-col divide-y divide-border">
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
                <div className="px-6 py-6 text-[14px] text-ink-variant">
                  {t('foodProfile.empty')}
                </div>
              )}
            </div>

            {profileEditorOpen && (
              <form
                onSubmit={handleSaveFoodProfile}
                noValidate
                className="border-t border-border px-6 py-5"
              >
                <div className="grid gap-4 sm:grid-cols-[1fr_160px]">
                  <label className="flex flex-col gap-2">
                    <span className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
                      {t('foodProfile.name')}
                    </span>
                    <Input
                      type="text"
                      value={foodProfileName}
                      onChange={(event) => setFoodProfileName(event.target.value)}
                      maxLength={150}
                      disabled={foodProfileSaving}
                    />
                  </label>
                  <label className="flex flex-col gap-2">
                    <span className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
                      {t('foodProfile.language')}
                    </span>
                    <Select
                      value={foodProfileLanguage}
                      onValueChange={setFoodProfileLanguage}
                      disabled={foodProfileSaving}
                    >
                      <SelectTrigger className="h-11 w-full min-w-0 rounded-xl border border-border bg-surface px-3 text-[15px] text-ink">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="vi">Tiếng Việt</SelectItem>
                        <SelectItem value="en">English</SelectItem>
                      </SelectContent>
                    </Select>
                  </label>
                </div>

                <label className="mt-4 flex items-center gap-2 text-[14px] text-ink">
                  <input
                    type="checkbox"
                    checked={foodProfileDefault}
                    onChange={(event) => setFoodProfileDefault(event.target.checked)}
                    disabled={foodProfileSaving || foodProfiles.length === 0}
                    className="size-4 accent-primary"
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
                  <Button
                    type="button"
                    variant="outline"
                    onClick={closeFoodProfileEditor}
                    disabled={foodProfileSaving}
                  >
                    <X className="size-4" aria-hidden />
                    {t('common.cancel')}
                  </Button>
                  <Button type="submit" disabled={foodProfileSaving}>
                    {foodProfileSaving ? (
                      <Loader2 className="size-4 animate-spin" aria-hidden />
                    ) : (
                      <Save className="size-4" aria-hidden />
                    )}
                    {t('common.save')}
                  </Button>
                </div>
              </form>
            )}
          </SectionCard>
        </Reveal>

        <Reveal delay={0.3}>
          <div className="mt-8 flex justify-center">
            <Button
              variant="outline"
              size="lg"
              className="w-full max-w-[300px] rounded-full border-destructive/30 text-[15px] font-bold text-destructive hover:bg-destructive/10"
              onClick={() => {
                setDeleteDialogStep(1)
                setDeleteEmailInput('')
                setDeleteSuccessMsg(null)
                setDeleteError(null)
                setDeleteDialogOpen(true)
              }}
            >
              <Trash2 className="mr-2 size-5" />
              {t('deleteAccount.deleteAccount')}
            </Button>
          </div>
        </Reveal>
      </div>

      {/* Delete Account Modal */}
      <AnimatePresence>
        {deleteDialogOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm"
              onClick={() => {
                if (!deleteRequesting && !deleteSuccessMsg) setDeleteDialogOpen(false)
              }}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-1/2 top-1/2 z-50 w-[90%] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl border border-border bg-surface p-6 shadow-3"
            >
              <h3 className="mb-2 text-[20px] font-bold text-destructive">
                {t('deleteAccount.deleteAccount')}
              </h3>

              <div className="text-left mt-4">
                {deleteSuccessMsg ? (
                  <div className="text-center py-4">
                    <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-success/10 mb-4">
                      <CheckCircle2 className="size-6 text-success" />
                    </div>
                    <h4 className="text-[16px] font-bold text-ink mb-2">
                      {t('deleteAccount.emailSent')}
                    </h4>
                    <p className="text-[14px] text-ink-variant">
                      {deleteSuccessMsg}
                    </p>
                    <Button 
                      size="lg"
                      className="mt-6 w-full rounded-xl"
                      onClick={() => setDeleteDialogOpen(false)}
                    >
                      Đóng
                    </Button>
                  </div>
                ) : deleteDialogStep === 1 ? (
                  <div className="flex flex-col gap-6">
                    <p className="text-[14px] text-destructive leading-relaxed">
                      ⚠️ <strong>Cảnh báo:</strong> {t('deleteAccount.warning')}
                    </p>
                    <div className="flex flex-col gap-3">
                      <Button 
                        type="button" 
                        variant="destructive"
                        size="lg"
                        className="rounded-xl"
                        onClick={() => setDeleteDialogStep(2)}
                      >
                        Tiếp tục
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="lg"
                        className="rounded-xl"
                        onClick={() => setDeleteDialogOpen(false)}
                      >
                        {t('common.cancel')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleRequestDelete} className="flex flex-col gap-4">
                    <p className="text-[14px] text-destructive">
                      {t('deleteAccount.typeEmailToConfirm')} <strong className="select-all text-destructive">{profile?.email}</strong>
                    </p>
                    
                    <input
                      type="email"
                      value={deleteEmailInput}
                      onChange={(e) => setDeleteEmailInput(e.target.value)}
                      placeholder={profile?.email}
                      required
                      disabled={deleteRequesting}
                      className="w-full rounded-xl border border-border bg-panel px-4 py-3 text-[14px] text-ink outline-none transition-colors focus:border-destructive focus:bg-surface"
                      autoFocus
                    />

                    {deleteError && (
                      <p className="flex items-center gap-2 text-[14px] font-medium text-destructive mt-1">
                        <AlertCircle className="size-4 shrink-0" />
                        {deleteError}
                      </p>
                    )}

                    <div className="flex flex-col gap-3 mt-4">
                      <Button 
                        type="submit" 
                        variant="destructive"
                        size="lg"
                        className="rounded-xl"
                        disabled={deleteRequesting || deleteEmailInput !== profile?.email}
                      >
                        {deleteRequesting ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
                        {t('deleteAccount.confirmDelete')}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="lg"
                        className="rounded-xl"
                        onClick={() => setDeleteDialogStep(1)}
                        disabled={deleteRequesting}
                      >
                        Trở lại
                      </Button>
                    </div>
                  </form>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </PageTransition>
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
    <div className="flex min-h-[96px] gap-3 px-6 py-4">
      <span className="mt-1 flex size-5 shrink-0 text-ink-variant">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="mb-1 text-[13px] uppercase tracking-[0.5px] text-ink-variant">
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
    <div className="flex min-h-[96px] gap-3 px-6 py-4">
      <span className="mt-1 flex size-5 shrink-0 text-ink-variant">
        {icon}
      </span>
      <label className="min-w-0 flex-1">
        <span className="mb-2 block text-[13px] uppercase tracking-[0.5px] text-ink-variant">
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
    <div className="flex flex-col gap-4 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-[17px] font-bold text-ink">
            {profile.display_name}
          </h3>
          {profile.is_default && (
            <Badge variant="default">
              <Star className="size-3" aria-hidden />
              {t('foodProfile.defaultBadge')}
            </Badge>
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
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={onEdit}
          disabled={deleting}
          aria-label={t('common.edit')}
        >
          <Pencil className="size-4" aria-hidden />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={onDelete}
          disabled={deleting}
          aria-label={t('common.delete')}
          className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  )
}
