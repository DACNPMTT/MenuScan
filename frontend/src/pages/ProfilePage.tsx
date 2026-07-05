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
  RefreshCw,
  Save,
  ShieldCheck,
  UserCircle,
  X,
} from 'lucide-react'
import { useAuth, type User } from '@/app/providers/AuthProvider'
import { ApiError, apiRequest } from '@/shared/lib/api'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

const LANGUAGE_LABELS: Record<string, string> = {
  vi: 'Tiếng Việt',
  en: 'English',
}

const ROLE_LABELS: Record<string, string> = {
  USER: 'Người dùng',
  ADMIN: 'Quản trị viên',
}

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Đang hoạt động',
  LOCKED: 'Đã khóa',
  DISABLED: 'Đã tắt',
}

const STATUS_STYLES: Record<string, string> = {
  ACTIVE: 'bg-[#e4f4df] text-[#256b2b]',
  LOCKED: 'bg-secondary text-ink-variant',
  DISABLED: 'bg-destructive/10 text-destructive',
}

function displayValue(value: string | null | undefined, fallback = 'Chưa thiết lập') {
  return value?.trim() ? value : fallback
}

function formatDate(value: string | undefined) {
  if (!value) return 'Chưa có dữ liệu'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('vi-VN', {
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
  useDocumentTitle('Profile | MenuScan')
  const { user, accessToken, updateProfile } = useAuth()
  const [fullProfile, setFullProfile] = useState<User | null>(null)
  const [loading, setLoading] = useState(Boolean(accessToken))
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [draftDisplayName, setDraftDisplayName] = useState('')
  const [draftLanguage, setDraftLanguage] = useState('vi')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

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
      setFullProfile(data)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Không thể tải đầy đủ thông tin tài khoản.',
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [accessToken])

  useEffect(() => {
    void Promise.resolve().then(() => loadProfile('initial'))
  }, [loadProfile])

  const profile = fullProfile ?? user

  const displayName = useMemo(
    () => displayValue(profile?.display_name, profile?.email.split('@')[0] ?? 'Người dùng'),
    [profile?.display_name, profile?.email],
  )
  const initials = useMemo(() => initialsFrom(displayName), [displayName])
  const language = LANGUAGE_LABELS[profile?.preferred_language ?? ''] ?? displayValue(profile?.preferred_language)
  const role = ROLE_LABELS[profile?.role ?? ''] ?? displayValue(profile?.role)
  const status = profile?.status ?? 'ACTIVE'
  const statusLabel = STATUS_LABELS[status] ?? status
  const statusStyle = STATUS_STYLES[status] ?? 'bg-secondary text-ink-variant'

  const startEditing = () => {
    setDraftDisplayName(profile?.display_name ?? '')
    setDraftLanguage(profile?.preferred_language === 'en' ? 'en' : 'vi')
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
      setSaveError('Tên hiển thị tối đa 150 ký tự.')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await updateProfile({
        display_name: normalizedDisplayName || null,
        preferred_language: draftLanguage,
      })
      setFullProfile(updated)
      setEditing(false)
    } catch (err) {
      setSaveError(
        err instanceof ApiError
          ? err.message
          : 'Không thể cập nhật profile. Vui lòng thử lại.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-[13px] font-bold uppercase tracking-[0.7px] text-ink-variant">
            Tài khoản
          </p>
          <h1 className="text-[32px] font-bold leading-[40px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
            Profile
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
          Làm mới
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
            Đang tải profile...
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
              Đặt mật khẩu
            </Link>
          </div>
        )}
      </section>

      <div className="mt-[20px]">
        <form onSubmit={handleSaveProfile} noValidate className="rounded-[12px] border border-hairline bg-canvas">
          <header className="flex flex-col gap-3 border-b border-hairline bg-app-bg px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-[20px] leading-[28px] text-primary-dark">
                Thông tin hồ sơ
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
                  Hủy
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
                  Lưu
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={startEditing}
                className="flex min-h-10 w-fit items-center gap-2 rounded-[8px] border border-primary-dark px-4 py-2 text-[14px] font-bold text-primary-dark transition-colors hover:bg-primary/10"
              >
                <Pencil className="size-4" aria-hidden />
                Chỉnh sửa
              </button>
            )}
          </header>
          <div className="grid grid-cols-1 divide-y divide-hairline sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            <div className="flex flex-col">
              {editing ? (
                <ProfileEditField
                  icon={<UserCircle className="size-5" />}
                  label="Tên hiển thị"
                >
                  <input
                    type="text"
                    value={draftDisplayName}
                    onChange={(event) => setDraftDisplayName(event.target.value)}
                    maxLength={150}
                    placeholder="Nhập tên hiển thị"
                    disabled={saving}
                    className="h-10 w-full min-w-0 rounded-[8px] border border-hairline bg-canvas px-3 text-[15px] text-ink outline-none transition-colors placeholder:text-placeholder focus:border-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  />
                </ProfileEditField>
              ) : (
                <ProfileField
                  icon={<UserCircle className="size-5" />}
                  label="Tên hiển thị"
                  value={displayValue(profile?.display_name)}
                />
              )}
              <ProfileField
                icon={<Mail className="size-5" />}
                label="Email"
                value={displayValue(profile?.email, 'Chưa có email')}
              />
              {editing ? (
                <ProfileEditField
                  icon={<Languages className="size-5" />}
                  label="Ngôn ngữ ưu tiên"
                >
                  <select
                    value={draftLanguage}
                    onChange={(event) => setDraftLanguage(event.target.value)}
                    disabled={saving}
                    className="h-10 w-full min-w-0 rounded-[8px] border border-hairline bg-canvas px-3 text-[15px] font-bold text-ink outline-none transition-colors focus:border-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="vi">Tiếng Việt</option>
                    <option value="en">English</option>
                  </select>
                </ProfileEditField>
              ) : (
                <ProfileField
                  icon={<Languages className="size-5" />}
                  label="Ngôn ngữ ưu tiên"
                  value={language}
                />
              )}
            </div>
            <div className="flex flex-col">
              <ProfileField
                icon={<ShieldCheck className="size-5" />}
                label="Vai trò"
                value={role}
              />
              <ProfileField
                icon={<BadgeCheck className="size-5" />}
                label="Trạng thái"
                value={statusLabel}
              />
              <ProfileField
                icon={<CalendarDays className="size-5" />}
                label="Ngày tạo"
                value={formatDate(profile?.created_at)}
              />
            </div>
          </div>
        </form>
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
      <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-[8px] bg-surface-muted text-primary-dark">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="mb-1 text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
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
      <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-[8px] bg-surface-muted text-primary-dark">
        {icon}
      </span>
      <label className="min-w-0 flex-1">
        <span className="mb-2 block text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
          {label}
        </span>
        {children}
      </label>
    </div>
  )
}
