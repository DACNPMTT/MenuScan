import { useEffect, useState, useRef } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import QRCode from 'qrcode'
import { motion } from 'motion/react'
import {
  Users,
  Clock,
  RefreshCw,
  Loader2,
  AlertCircle,
  Maximize2,
  Minimize2,
  ArrowLeft,
  CheckCircle,
  HelpCircle,
  ScanLine,
  Trash2,
} from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { apiRequest, ApiError } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card } from '@/shared/components/ui/card'
import { EmptyState } from '@/shared/components/EmptyState'
import { Reveal } from '@/shared/components/motion/Reveal'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

interface DiningPreference {
  id: string
  code: string
  category: string
  preference_type: 'LIKE' | 'DISLIKE' | 'AVOID' | 'ALLERGY' | 'DIETARY_RULE'
  intensity: number | null
  importance: number
  note: string | null
}

interface DiningParticipant {
  id: string
  display_name: string
  joined_at: string
  preferences: DiningPreference[]
}

interface DiningSessionDetail {
  id: string
  created_by_user_id: string | null
  mode: 'GROUP' | 'PERSONAL'
  status: 'COLLECTING' | 'SCANNING' | 'COMPLETED' | 'CLOSED'
  participant_count: number
  participants: DiningParticipant[]
  created_at: string
  updated_at: string
}

export function HostDiningSessionPage() {
  const { t } = useTranslation()
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  useDocumentTitle(`Host Session ${sessionId?.slice(0, 8) ?? ''} | MenuScan`)
  const { accessToken } = useAuth()

  const [session, setSession] = useState<DiningSessionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pollingActive] = useState(true)

  // QR Code state
  const [inviteToken, setInviteToken] = useState<string | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState<string>('')
  const [isFullscreenQr, setIsFullscreenQr] = useState(false)

  const joinUrl = inviteToken ? `${window.location.origin}/dining/join?token=${inviteToken}` : ''

  // Fetch session function
  const fetchSession = async (showLoading = false) => {
    if (!sessionId) return
    if (showLoading) setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<DiningSessionDetail>(`/api/v1/dining/sessions/${sessionId}`, {
        method: 'GET',
        token: accessToken ?? undefined,
      })
      setSession(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Không thể tải chi tiết phiên ăn.')
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const handleDeleteParticipant = async (participantId: string) => {
    if (!sessionId) return
    if (!window.confirm("Bạn có chắc chắn muốn xóa người tham gia này khỏi phiên ăn?")) return

    try {
      await apiRequest(`/api/v1/dining/sessions/${sessionId}/participants/${participantId}`, {
        method: 'DELETE',
        token: accessToken ?? undefined,
      })
      await fetchSession(false)
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Không thể xóa người tham gia.')
    }
  }

  // Handle invite token from navigation state or localStorage
  useEffect(() => {
    if (!sessionId) return

    const stateToken = (location.state as { inviteToken?: string } | null)?.inviteToken
    const storageKey = `dining_invite_${sessionId}`

    let active = true
    Promise.resolve().then(() => {
      if (!active) return
      if (stateToken) {
        setInviteToken(stateToken)
        localStorage.setItem(storageKey, stateToken)
      } else {
        const savedToken = localStorage.getItem(storageKey)
        if (savedToken) {
          setInviteToken(savedToken)
        }
      }
    })
    return () => {
      active = false
    }
  }, [sessionId, location.state])

  // Generate QR Code URL
  useEffect(() => {
    if (!inviteToken) return
    const joinUrl = `${window.location.origin}/dining/join?token=${inviteToken}`

    QRCode.toDataURL(joinUrl, {
      width: 512,
      margin: 1,
      color: {
        dark: '#042c60', // navy ink — scans cleanly on white
        light: '#ffffff',
      },
    })
      .then(setQrDataUrl)
      .catch((err) => console.error('Failed to generate QR code:', err))
  }, [inviteToken])

  // Polling effect
  const pollTimerRef = useRef<number | undefined>(undefined)
  useEffect(() => {
    let active = true
    Promise.resolve().then(() => {
      if (active) void fetchSession(true)
    })

    // Poll every 5 seconds
    pollTimerRef.current = window.setInterval(() => {
      if (pollingActive) {
        void fetchSession(false)
      }
    }, 5000)

    return () => {
      active = false
      clearInterval(pollTimerRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, pollingActive])

  const formatDate = (isoString: string) => {
    const date = new Date(isoString)
    if (Number.isNaN(date.getTime())) return isoString
    return new Intl.DateTimeFormat('vi-VN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date)
  }

  const getPreferenceBadgeStyle = (type: DiningPreference['preference_type']) => {
    switch (type) {
      case 'ALLERGY':
        return 'border-destructive/40 bg-destructive/10 text-destructive'
      case 'AVOID':
        return 'border-amber/40 bg-amber/15 text-amber'
      case 'DIETARY_RULE':
        return 'border-primary/30 bg-primary/15 text-primary-dark'
      case 'LIKE':
        return 'border-success/30 bg-success/15 text-success'
      default:
        return 'border-border bg-panel text-ink-variant'
    }
  }

  const getPreferenceTypeLabel = (type: DiningPreference['preference_type']) => {
    switch (type) {
      case 'ALLERGY':
        return 'Dị ứng'
      case 'AVOID':
        return 'Hạn chế'
      case 'DIETARY_RULE':
        return 'Ăn kiêng'
      case 'LIKE':
        return 'Thích'
      default:
        return 'Khác'
    }
  }

  if (loading) {
    return (
      <PageTransition className="flex h-[60vh] w-full flex-col items-center justify-center text-ink-variant">
        <Loader2 className="mb-3 size-10 animate-spin text-primary" aria-hidden />
        <p className="text-[15px] font-medium">{t('common.loading') || 'Loading...'}</p>
      </PageTransition>
    )
  }

  if (error || !session) {
    return (
      <PageTransition className="mx-auto max-w-[600px] px-4 py-16">
        <EmptyState
          icon={AlertCircle}
          tone="destructive"
          title="Đã xảy ra lỗi"
          description={error || 'Không tìm thấy phiên ăn.'}
          action={
            <Button variant="outline" asChild>
              <Link to="/app/dining">
                <ArrowLeft className="size-4" aria-hidden /> Quay lại danh sách
              </Link>
            </Button>
          }
        />
      </PageTransition>
    )
  }

  return (
    <PageTransition className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      {/* Back button */}
      <Button variant="ghost" size="sm" asChild className="mb-6 -ml-2">
        <Link to="/app/dining">
          <ArrowLeft className="size-4" aria-hidden />
          {t('common.back') || 'Quay lại'}
        </Link>
      </Button>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
        {/* Left column: QR code sharing */}
        <Card className="w-full shrink-0 items-center gap-4 rounded-3xl p-6 text-center shadow-3 lg:max-w-[420px]">
          <div className="flex w-full flex-col gap-1">
            <h2 className="text-[22px] font-bold text-ink">{t('dining.scanQrPrompt')}</h2>
            <p className="px-2 text-[14px] text-ink-variant">{t('dining.scanQrDesc')}</p>
          </div>

          {/* QR Display */}
          {qrDataUrl ? (
            <div className="group flex flex-col items-center">
              <div className="relative max-w-[280px] rounded-2xl border-4 border-primary/20 bg-white p-2">
                <img
                  src={qrDataUrl}
                  alt="Dining Invite QR Code"
                  className="aspect-square w-full rounded-xl"
                />
                <Button
                  type="button"
                  variant="default"
                  size="icon-sm"
                  onClick={() => setIsFullscreenQr(true)}
                  className="absolute bottom-4 right-4 shadow-2"
                  title={t('dining.fullscreenQr')}
                  aria-label={t('dining.fullscreenQr')}
                >
                  <Maximize2 className="size-4" />
                </Button>
              </div>
              <button
                type="button"
                onClick={() => setIsFullscreenQr(true)}
                className="mt-2.5 flex items-center gap-1 text-[13px] font-bold text-primary hover:text-primary-dark"
              >
                <Maximize2 className="size-3.5" aria-hidden />
                {t('dining.fullscreenQr')}
              </button>

              <div className="mt-4 flex w-full max-w-[280px] flex-col items-center gap-1.5">
                <span className="text-[12px] font-medium text-ink-variant">
                  Hoặc nhấp vào liên kết trực tiếp:
                </span>
                <a
                  href={joinUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full truncate rounded-xl border border-primary/20 bg-panel px-3 py-2 text-center text-[12px] font-semibold text-primary-dark transition-colors hover:bg-border"
                  title={joinUrl}
                >
                  {joinUrl}
                </a>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-destructive/30 bg-destructive/5 p-4 text-center">
              <AlertCircle className="mb-2 size-8 text-destructive" aria-hidden />
              <p className="mb-1 text-[13px] font-semibold text-destructive">
                Không thể hiển thị QR code
              </p>
              <p className="max-w-[260px] text-[12px] text-ink-variant">
                Token mời đã bị thiếu do tải lại trang trên thiết bị khác. Mọi người vẫn có thể tham
                gia nếu bạn chia sẻ link trực tiếp.
              </p>
            </div>
          )}

          {/* Session short details */}
          <div className="mt-2 w-full border-t border-hairline pt-4 text-left">
            <div className="flex items-center justify-between text-[14px]">
              <span className="flex items-center gap-1.5 text-ink-variant">
                <Clock className="size-4" aria-hidden />
                Khởi tạo:
              </span>
              <span className="font-medium text-ink-variant">{formatDate(session.created_at)}</span>
            </div>
            <div className="flex items-center justify-between text-[14px]">
              <span className="flex items-center gap-1.5 text-ink-variant">
                <HelpCircle className="size-4" aria-hidden />
                Trạng thái:
              </span>
              <Badge variant="secondary" className="text-[11px] font-bold">
                {t(`dining.status.${session.status}`)}
              </Badge>
            </div>
          </div>

          <Button asChild size="lg" className="mt-2 w-full">
            <Link to={`/app/scan?dining_session_id=${session.id}`}>
              <ScanLine className="size-5" aria-hidden />
              Quét thực đơn phiên này
            </Link>
          </Button>
        </Card>

        {/* Right column: Participants and their preferences */}
        <div className="flex flex-1 flex-col gap-4">
          <div className="flex items-center justify-between border-b border-hairline pb-3">
            <h2 className="flex items-center gap-2 text-[22px] font-bold text-ink">
              <Users className="size-5 text-primary" aria-hidden />
              {t('dining.participants', { count: session.participants.length })}
            </h2>
            <div className="flex items-center gap-3">
              {pollingActive && (
                <span className="flex items-center gap-1.5 text-[12px] font-medium text-success">
                  <span className="relative flex size-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex size-2 rounded-full bg-success" />
                  </span>
                  Đang cập nhật trực tiếp
                </span>
              )}
              <Button
                onClick={() => void fetchSession(false)}
                variant="outline"
                size="icon-sm"
                aria-label="Refresh"
              >
                <RefreshCw className="size-4" />
              </Button>
            </div>
          </div>

          {session.participants.length === 0 ? (
            <EmptyState
              icon={Users}
              tone="primary"
              title="Chưa có ai tham gia"
              description={t('dining.noParticipants')}
            />
          ) : (
            <div className="flex flex-col gap-4">
              {session.participants.map((participant, index) => (
                <Reveal key={participant.id} delay={index * 0.05}>
                  <Card className="gap-3 rounded-2xl p-5 shadow-1 transition-all duration-200 ease-[var(--ease-out-quint)] hover:-translate-y-1 hover:shadow-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex size-9 items-center justify-center rounded-full bg-primary text-[14px] font-bold text-white shadow-2 shadow-primary/30">
                          {participant.display_name.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[16px] font-bold leading-tight text-ink">
                            {participant.display_name}
                          </span>
                          <span className="text-[11px] text-ink-variant">
                            Đã tham gia{' '}
                            {new Intl.DateTimeFormat('vi-VN', { timeStyle: 'short' }).format(
                              new Date(participant.joined_at),
                            )}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-[12px] font-medium text-primary">
                          <CheckCircle className="size-4 text-primary" aria-hidden /> Đã gửi sở thích
                        </span>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon-sm"
                          onClick={() => handleDeleteParticipant(participant.id)}
                          title="Xóa người tham gia"
                          aria-label="Xóa người tham gia"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Preferences chips list */}
                    <div className="border-t border-hairline/60 pt-3">
                      {participant.preferences.length === 0 ? (
                        <p className="text-[13px] italic text-ink-variant">
                          Không khai báo sở thích ăn uống đặc biệt.
                        </p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {participant.preferences.map((pref) => (
                            <div
                              key={pref.id}
                              className={`inline-flex items-center rounded-full border px-3 py-1 text-[12px] font-bold ${getPreferenceBadgeStyle(
                                pref.preference_type,
                              )}`}
                            >
                              <span className="mr-1.5 rounded bg-black/5 px-1 text-[9px] uppercase opacity-80">
                                {getPreferenceTypeLabel(pref.preference_type)}
                              </span>
                              <span className="capitalize">{pref.code.replace(/_/g, ' ')}</span>
                              {pref.intensity !== null && (
                                <span className="ml-1 text-[10px] opacity-80">
                                  ({pref.intensity}/5)
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </Card>
                </Reveal>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen QR Modal Overlay */}
      {isFullscreenQr && qrDataUrl && (
        <div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90 p-4"
          onClick={() => setIsFullscreenQr(false)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="flex w-full max-w-[500px] flex-col items-center gap-6 rounded-3xl bg-white p-8 text-center shadow-pop"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col gap-1">
              <h3 className="text-[24px] font-bold text-ink">{t('dining.scanQrPrompt')}</h3>
              <p className="max-w-[360px] text-[14px] text-ink-variant">{t('dining.scanQrDesc')}</p>
            </div>

            <img
              src={qrDataUrl}
              alt="Dining Session Fullscreen QR Code"
              className="aspect-square w-full max-w-[360px] rounded-2xl border border-hairline shadow-inner"
            />

            <Button onClick={() => setIsFullscreenQr(false)} size="lg" className="px-8">
              <Minimize2 className="size-4" aria-hidden />
              {t('dining.closeFullscreen')}
            </Button>
          </motion.div>
        </div>
      )}
    </PageTransition>
  )
}
