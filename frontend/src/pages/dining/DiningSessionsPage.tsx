import { useEffect, useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import { useTranslation } from 'react-i18next'
import {
  Users,
  Calendar,
  ChevronRight,
  Loader2,
  AlertCircle,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { Spinner } from '@/shared/components/Spinner'
import { useAuth } from '@/app/providers/AuthProvider'
import { apiRequest } from '@/shared/lib/api'
import { describeError } from '@/shared/lib/errors'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card } from '@/shared/components/ui/card'
import { EmptyState } from '@/shared/components/EmptyState'
import { Reveal } from '@/shared/components/motion/Reveal'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { SectionCard } from '@/shared/components/SectionCard'
import { Pagination } from '@/shared/components/ui/pagination'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

interface DiningSessionSummary {
  id: string
  name: string | null
  created_by_user_id: string | null
  mode: 'GROUP' | 'PERSONAL'
  status: 'COLLECTING' | 'SCANNING' | 'COMPLETED' | 'CLOSED'
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

  const [currentPage, setCurrentPage] = useState(1)
  const PAGE_SIZE = 5

  // Creation form state
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [sessionNameInput, setSessionNameInput] = useState('')

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
      setError(describeError(err, t, 'errors.generic'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.resolve().then(() => {
      if (active) void loadSessions()
    })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const totalPages = Math.ceil(sessions.length / PAGE_SIZE)
  const paginatedSessions = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return sessions.slice(start, start + PAGE_SIZE)
  }, [sessions, currentPage])

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
          invite_expires_in_hours: null,
          name: sessionNameInput.trim() || null,
        }),
      })
      navigate(`/app/dining/sessions/${result.session.id}`, {
        state: { inviteToken: result.invite_token },
      })
    } catch (err) {
      setCreateError(describeError(err, t, 'errors.generic'))
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
      alert(describeError(err, t, 'errors.generic'))
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
    <PageTransition className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      <div className="flex flex-col gap-2">
        <h1 className="text-[32px] font-bold leading-[40px] text-ink sm:text-[44px] sm:leading-[52px]">
          {t('dining.title')}
        </h1>
        <p className="flex items-center gap-2 text-[14px] text-ink-variant">
          <Sparkles className="size-4 text-amber" aria-hidden />
          {t('dining.createSubtitle')}
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_360px]">
        {/* Left column: List of sessions */}
        <div className="flex flex-col gap-4">
          <h2 className="border-b border-hairline pb-2 text-[20px] font-bold text-ink">
            {t('dining.recentSessions')}
          </h2>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-ink-variant">
              <Spinner label={t('common.loading') || 'Loading...'} />
            </div>
          ) : error ? (
            <EmptyState
              icon={AlertCircle}
              tone="destructive"
              title={error}
              action={
                <Button variant="outline" onClick={loadSessions}>
                  {t('common.retry') || 'Retry'}
                </Button>
              }
            />
          ) : sessions.length === 0 ? (
            <EmptyState
              icon={Users}
              tone="primary"
              title={t('dining.noParticipants').replace(/Mã QR.*/, '')}
              description="Chưa có phiên ăn uống nào. Hãy tạo phiên ăn uống đầu tiên của bạn ở biểu mẫu bên cạnh!"
            />
          ) : (
            <div className="flex flex-col gap-3">
              {paginatedSessions.map((session, index) => (
                <Reveal key={session.id} delay={index * 0.05}>
                  <Link to={`/app/dining/sessions/${session.id}`} className="group block">
                    <Card className="flex-row items-center justify-between gap-4 rounded-2xl p-4 shadow-1 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-1 hover:shadow-3">
                      <div className="flex min-w-0 flex-col gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`text-[15px] font-bold tracking-wide text-ink ${session.name ? '' : 'uppercase'}`}>
                            {session.name || `Session: ${session.id.slice(0, 8)}`}
                          </span>
                          <Badge
                            variant={session.status === 'COLLECTING' ? 'accent' : 'secondary'}
                            className="text-[11px]"
                          >
                            {t(`dining.status.${session.status}`)}
                          </Badge>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-variant">
                          <span className="flex items-center gap-1">
                            <Users className="size-3.5" aria-hidden />
                            {t('dining.participants', { count: session.participant_count })}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="size-3.5" aria-hidden />
                            {formatDate(session.created_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="icon-sm"
                          onClick={(e) => handleDeleteSession(e, session.id)}
                          title="Xóa phiên ăn"
                          aria-label="Xóa phiên ăn"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                        <ChevronRight
                          className="size-5 text-ink-variant transition-transform group-hover:translate-x-1"
                          aria-hidden
                        />
                      </div>
                    </Card>
                  </Link>
                </Reveal>
              ))}
              {totalPages > 1 && (
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                />
              )}
            </div>
          )}
        </div>

        {/* Right column: Create Session Button */}
        <SectionCard
          title={t('dining.createTitle')}
          description="Thiết lập thông tin bàn ăn để bắt đầu chia sẻ."
          className="h-fit"
        >
          <Button
            type="button"
            size="lg"
            className="mt-2 w-full"
            onClick={() => {
              setSessionNameInput('')
              setCreateError(null)
              setIsCreateModalOpen(true)
            }}
          >
            {t('dining.createBtn')}
          </Button>
        </SectionCard>
      </div>

      <AnimatePresence>
        {isCreateModalOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm"
              onClick={() => !creating && setIsCreateModalOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-1/2 top-1/2 z-50 w-[90%] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl border border-border bg-surface p-6 shadow-3"
            >
              <h3 className="mb-2 text-[20px] font-bold text-ink">
                Tên phiên ăn
              </h3>
              <p className="mb-5 text-[14px] text-ink-variant">
                Nhập tên gợi nhớ cho phiên ăn này (ví dụ: "Ăn trưa với team"). Bỏ trống để dùng mã mặc định.
              </p>

              <form onSubmit={handleCreateSession} className="flex flex-col gap-4">
                <input
                  type="text"
                  value={sessionNameInput}
                  onChange={(e) => setSessionNameInput(e.target.value)}
                  placeholder="Tên phiên ăn (tùy chọn)"
                  className="w-full rounded-xl border border-border bg-panel px-4 py-3 text-[14px] text-ink outline-none transition-colors focus:border-primary focus:bg-surface"
                  autoFocus
                  disabled={creating}
                />

                {createError && (
                  <p className="flex items-center gap-1.5 text-[13px] font-medium text-destructive">
                    <AlertCircle className="size-4 shrink-0" aria-hidden />
                    {createError}
                  </p>
                )}

                <div className="mt-2 flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsCreateModalOpen(false)}
                    disabled={creating}
                  >
                    Hủy
                  </Button>
                  <Button type="submit" disabled={creating}>
                    {creating && <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />}
                    {creating ? t('dining.creating') : t('dining.createBtn')}
                  </Button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </PageTransition>
  )
}
