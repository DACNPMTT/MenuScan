import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Plus,
  Users,
  Globe,
  Clock,
  Calendar,
  ChevronRight,
  Loader2,
  AlertCircle,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

interface DiningSessionSummary {
  id: string
  created_by_user_id: string | null
  mode: 'GROUP' | 'PERSONAL'
  status: 'COLLECTING' | 'SCANNING' | 'COMPLETED' | 'CLOSED'
  target_language: string
  participant_count: number
  created_at: string
  updated_at: string
}

export function DiningSessionsPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('dining.title')} | MenuScan`)
  const { accessToken } = useAuth()
  const navigate = useNavigate()

  const [sessions, setSessions] = useState<DiningSessionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Creation form state
  const [targetLanguage, setTargetLanguage] = useState('vi')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const loadSessions = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<DiningSessionSummary[]>('/api/v1/dining/sessions', {
        method: 'GET',
        token: accessToken ?? undefined,
      })
      setSessions(data)
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : t('common.error') || 'Failed to load sessions',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSessions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setCreateError(null)
    try {
      const result = await apiRequest<{
        session: DiningSessionSummary
        invite_token: string
      }>('/api/v1/dining/sessions', {
        method: 'POST',
        token: accessToken ?? undefined,
        body: JSON.stringify({
          mode: 'GROUP',
          target_language: targetLanguage,
          invite_expires_in_hours: null,
        }),
      })
      navigate(`/app/dining/sessions/${result.session.id}`, {
        state: { inviteToken: result.invite_token },
      })
    } catch (err) {
      setCreateError(
        err instanceof ApiError ? err.message : t('common.error') || 'Failed to create session',
      )
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteSession = async (e: React.MouseEvent, targetSessionId: string) => {
    e.preventDefault()
    e.stopPropagation()
    if (!window.confirm("Bạn có chắc chắn muốn xóa phiên ăn này?")) return

    try {
      await apiRequest(`/api/v1/dining/sessions/${targetSessionId}`, {
        method: 'DELETE',
        token: accessToken ?? undefined,
      })
      await loadSessions()
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Không thể xóa phiên ăn.")
    }
  }

  const formatDate = (isoString: string) => {
    const date = new Date(isoString)
    if (Number.isNaN(date.getTime())) return isoString
    return new Intl.DateTimeFormat('vi-VN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date)
  }

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px] font-sans">
      <div className="flex flex-col gap-2">
        <h1 className="text-[32px] font-bold leading-[40px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
          {t('dining.title')}
        </h1>
        <p className="flex items-center gap-2 text-[14px] text-ink-variant">
          <Sparkles className="size-4 text-primary-dark" aria-hidden />
          {t('dining.createSubtitle')}
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_360px]">
        {/* Left column: List of sessions */}
        <div className="flex flex-col gap-4">
          <h2 className="text-[20px] font-bold text-primary-dark border-b border-hairline pb-2">
            {t('dining.recentSessions')}
          </h2>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-ink-variant">
              <Loader2 className="size-8 animate-spin text-primary-dark mb-2" />
              <p className="text-[14px]">{t('common.loading') || 'Loading...'}</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 border border-dashed border-destructive/30 rounded-[12px] bg-destructive/5 text-center px-4">
              <AlertCircle className="size-8 text-destructive mb-2" />
              <p className="text-[14px] text-destructive font-medium mb-3">{error}</p>
              <Button onClick={loadSessions} variant="outline" className="h-9">
                {t('common.retry') || 'Retry'}
              </Button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border border-dashed border-hairline rounded-[12px] bg-canvas text-center px-4">
              <Users className="size-12 text-ink-variant mb-3" />
              <p className="text-[16px] font-medium text-ink mb-1">
                {t('dining.noParticipants').replace(/Mã QR.*/, '')}
              </p>
              <p className="text-[14px] text-ink-variant max-w-[360px] mb-4">
                Chưa có phiên ăn uống nào. Hãy tạo phiên ăn uống đầu tiên của bạn ở biểu mẫu bên cạnh!
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {sessions.map((session) => (
                <Link
                  key={session.id}
                  to={`/app/dining/sessions/${session.id}`}
                  className="group flex items-center justify-between rounded-[12px] border border-hairline bg-canvas p-4 transition-colors hover:bg-surface-muted"
                >
                  <div className="flex flex-col gap-2 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[15px] font-bold text-ink uppercase tracking-wide">
                        Session: {session.id.slice(0, 8)}
                      </span>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                          session.status === 'COLLECTING'
                            ? 'bg-[#e4f4df] text-[#256b2b]'
                            : 'bg-secondary text-ink-variant'
                        }`}
                      >
                        {t(`dining.status.${session.status}`)}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-variant">
                      <span className="flex items-center gap-1">
                        <Users className="size-3.5" />
                        {t('dining.participants', { count: session.participant_count })}
                      </span>
                      <span className="flex items-center gap-1">
                        <Globe className="size-3.5" />
                        {session.target_language.toUpperCase()}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="size-3.5" />
                        {formatDate(session.created_at)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={(e) => handleDeleteSession(e, session.id)}
                      className="flex size-9 items-center justify-center rounded-full text-ink-variant hover:text-destructive hover:bg-destructive/10 transition-colors"
                      title="Xóa phiên ăn"
                    >
                      <Trash2 className="size-4" />
                    </button>
                    <ChevronRight className="size-5 text-ink-variant transition-transform group-hover:translate-x-1" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Right column: Create Session Form */}
        <div className="rounded-[12px] border border-hairline bg-canvas p-5 shadow-sm h-fit">
          <h2 className="text-[18px] font-bold text-primary-dark mb-1">
            {t('dining.createTitle')}
          </h2>
          <p className="text-[13px] text-ink-variant mb-4">
            Thiết lập thông tin bàn ăn để bắt đầu chia sẻ.
          </p>

          <form onSubmit={handleCreateSession} className="flex flex-col gap-4">

            <div className="flex flex-col gap-1.5">
              <label htmlFor="dining-lang" className="text-[13px] font-bold uppercase tracking-[0.5px] text-ink-variant">
                {t('dining.fields.language')}
              </label>
              <select
                id="dining-lang"
                value={targetLanguage}
                onChange={(e) => setTargetLanguage(e.target.value)}
                className="h-10 rounded-[8px] border border-hairline bg-canvas px-3 text-[14px] text-primary-dark focus:outline-none focus:ring-1 focus:ring-primary-dark"
              >
                <option value="vi">Tiếng Việt (VI)</option>
                <option value="en">English (EN)</option>
              </select>
            </div>


            {createError && (
              <p className="text-[13px] text-destructive font-medium flex items-center gap-1.5">
                <AlertCircle className="size-4 shrink-0" />
                {createError}
              </p>
            )}

            <Button
              type="submit"
              disabled={creating}
              className="mt-2 h-11 w-full bg-primary-dark font-bold text-white rounded-[8px] hover:bg-primary-dark/95"
            >
              {creating && <Loader2 className="size-4 animate-spin mr-2 inline" />}
              {creating ? t('dining.creating') : t('dining.createBtn')}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
