import { useEffect, useState, useRef } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import QRCode from 'qrcode'
import {
  Users,
  Globe,
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
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'
import { Badge } from '@/shared/components/ui/badge'

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
  preferred_language: string
  joined_at: string
  preferences: DiningPreference[]
}

interface DiningSessionDetail {
  id: string
  created_by_user_id: string | null
  mode: 'GROUP' | 'PERSONAL'
  status: 'COLLECTING' | 'SCANNING' | 'COMPLETED' | 'CLOSED'
  target_language: string
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
  const [pollingActive, setPollingActive] = useState(true)

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

    if (stateToken) {
      setInviteToken(stateToken)
      localStorage.setItem(storageKey, stateToken)
    } else {
      const savedToken = localStorage.getItem(storageKey)
      if (savedToken) {
        setInviteToken(savedToken)
      }
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
        dark: '#1c2e15', // Matches primary-dark color
        light: '#ffffff',
      },
    })
      .then(setQrDataUrl)
      .catch((err) => console.error('Failed to generate QR code:', err))
  }, [inviteToken])

  // Polling effect
  const pollTimerRef = useRef<number | null>(null)
  useEffect(() => {
    void fetchSession(true)

    // Poll every 5 seconds
    pollTimerRef.current = window.setInterval(() => {
      if (pollingActive) {
        void fetchSession(false)
      }
    }, 5000)

    return () => {
      if (pollTimerRef.current !== null) {
        clearInterval(pollTimerRef.current)
      }
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
        return 'border-destructive bg-destructive/10 text-destructive'
      case 'AVOID':
        return 'border-[#e67e22] bg-[#e67e22]/10 text-[#e67e22]'
      case 'DIETARY_RULE':
        return 'border-[#9b59b6] bg-[#9b59b6]/10 text-[#9b59b6]'
      case 'LIKE':
        return 'border-[#2ecc71] bg-[#2ecc71]/10 text-[#27ae60]'
      default:
        return 'border-hairline bg-surface-muted text-ink-variant'
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
      <div className="flex h-[60vh] w-full flex-col items-center justify-center text-ink-variant">
        <Loader2 className="size-10 animate-spin text-primary-dark mb-3" />
        <p className="text-[15px] font-medium">{t('common.loading') || 'Loading...'}</p>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="mx-auto max-w-[600px] px-4 py-16 text-center">
        <AlertCircle className="size-12 text-destructive mx-auto mb-4" />
        <h2 className="text-[22px] font-bold text-primary-dark mb-2">Đã xảy ra lỗi</h2>
        <p className="text-[15px] text-ink-variant mb-6">{error || 'Không tìm thấy phiên ăn.'}</p>
        <Link to="/app/dining">
          <Button variant="outline" className="h-10">
            <ArrowLeft className="size-4 mr-2" /> Quay lại danh sách
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px] font-sans">
      {/* Back button */}
      <Link
        to="/app/dining"
        className="inline-flex items-center text-[14px] font-medium text-ink-variant hover:text-primary-dark mb-6 transition-colors"
      >
        <ArrowLeft className="size-4 mr-1.5" />
        {t('common.back') || 'Quay lại'}
      </Link>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
        {/* Left column: QR code sharing */}
        <div className="flex flex-col items-center gap-4 rounded-[16px] border border-hairline bg-canvas p-6 text-center shadow-sm w-full lg:max-w-[420px] shrink-0">
          <div className="flex flex-col gap-1 w-full">
            <h2 className="text-[22px] font-bold text-primary-dark">{t('dining.scanQrPrompt')}</h2>
            <p className="text-[14px] text-ink-variant px-2">{t('dining.scanQrDesc')}</p>
          </div>

          {/* QR Display */}
          {qrDataUrl ? (
            <div className="relative group flex flex-col items-center">
              <div className="relative border-4 border-primary/20 rounded-[12px] p-2 bg-white max-w-[280px]">
                <img
                  src={qrDataUrl}
                  alt="Dining Invite QR Code"
                  className="w-full aspect-square rounded-[8px]"
                />
                <button
                  type="button"
                  onClick={() => setIsFullscreenQr(true)}
                  className="absolute bottom-4 right-4 flex size-9 items-center justify-center rounded-full bg-primary-dark/80 text-white shadow-md backdrop-blur-xs transition-transform group-hover:scale-105 hover:bg-primary-dark"
                  title={t('dining.fullscreenQr')}
                >
                  <Maximize2 className="size-4" />
                </button>
              </div>
              <button
                type="button"
                onClick={() => setIsFullscreenQr(true)}
                className="mt-2.5 text-[13px] font-bold text-primary-dark hover:underline flex items-center gap-1"
              >
                <Maximize2 className="size-3.5" />
                {t('dining.fullscreenQr')}
              </button>
              
              <div className="mt-4 flex flex-col items-center gap-1.5 w-full max-w-[280px]">
                <span className="text-[12px] text-ink-variant font-medium">Hoặc nhấp vào liên kết trực tiếp:</span>
                <a
                  href={joinUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full text-[12px] font-semibold text-primary-dark bg-secondary/25 hover:bg-secondary/40 py-2 px-3 rounded-[8px] truncate block text-center border border-primary-dark/10 transition-colors"
                  title={joinUrl}
                >
                  {joinUrl}
                </a>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center border border-dashed border-destructive/30 rounded-[12px] bg-destructive/5 p-4 text-center">
              <AlertCircle className="size-8 text-destructive mb-2" />
              <p className="text-[13px] text-destructive font-semibold mb-1">
                Không thể hiển thị QR code
              </p>
              <p className="text-[12px] text-ink-variant max-w-[260px]">
                Token mời đã bị thiếu do tải lại trang trên thiết bị khác. Mọi người vẫn có thể tham gia nếu bạn chia sẻ link trực tiếp.
              </p>
            </div>
          )}

          {/* Session short details */}
          <div className="w-full border-t border-hairline mt-2 pt-4 flex flex-col gap-3 text-left">
            <div className="flex justify-between items-center text-[14px]">
              <span className="text-ink-variant flex items-center gap-1.5">
                <Globe className="size-4" />
                {t('dining.fields.language')}:
              </span>
              <span className="font-bold text-primary-dark uppercase">
                {session.target_language}
              </span>
            </div>
            <div className="flex justify-between items-center text-[14px]">
              <span className="text-ink-variant flex items-center gap-1.5">
                <Clock className="size-4" />
                Khởi tạo:
              </span>
              <span className="font-medium text-ink-variant">
                {formatDate(session.created_at)}
              </span>
            </div>
            <div className="flex justify-between items-center text-[14px]">
              <span className="text-ink-variant flex items-center gap-1.5">
                <HelpCircle className="size-4" />
                Trạng thái:
              </span>
              <Badge variant="outline" className="font-bold text-[11px] bg-secondary/15">
                {t(`dining.status.${session.status}`)}
              </Badge>
            </div>
          </div>

          <Link
            to={`/app/scan?dining_session_id=${session.id}`}
            className="w-full mt-2"
          >
            <Button className="w-full h-11 bg-primary-dark font-bold text-white rounded-[8px] hover:bg-primary-dark/95 flex items-center justify-center gap-2">
              <ScanLine className="size-5" />
              Quét thực đơn phiên này
            </Button>
          </Link>
        </div>

        {/* Right column: Participants and their preferences */}
        <div className="flex-1 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-hairline pb-3">
            <h2 className="text-[22px] font-bold text-primary-dark flex items-center gap-2">
              <Users className="size-5 text-primary-dark" />
              {t('dining.participants', { count: session.participants.length })}
            </h2>
            <div className="flex items-center gap-3">
              {pollingActive && (
                <span className="flex items-center gap-1.5 text-[12px] text-green-600 font-medium">
                  <span className="relative flex size-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full size-2 bg-green-500"></span>
                  </span>
                  Đang cập nhật trực tiếp
                </span>
              )}
              <Button
                onClick={() => void fetchSession(false)}
                variant="outline"
                className="h-9 px-3"
              >
                <RefreshCw className="size-4" />
              </Button>
            </div>
          </div>

          {session.participants.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 border border-dashed border-hairline rounded-[16px] bg-canvas text-center px-4">
              <Users className="size-14 text-ink-variant mb-3" />
              <p className="text-[16px] font-semibold text-ink mb-1.5">Chưa có ai tham gia</p>
              <p className="text-[14px] text-ink-variant max-w-[360px]">
                {t('dining.noParticipants')}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {session.participants.map((participant) => (
                <div
                  key={participant.id}
                  className="rounded-[16px] border border-hairline bg-canvas p-5 shadow-xs flex flex-col gap-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex size-9 items-center justify-center rounded-full bg-primary-dark text-white font-bold text-[14px]">
                        {participant.display_name.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[16px] font-bold text-primary-dark leading-tight">
                          {participant.display_name}
                        </span>
                        <span className="text-[11px] text-ink-variant">
                          Ngôn ngữ: {participant.preferred_language.toUpperCase()} • Đã tham gia{' '}
                          {new Intl.DateTimeFormat('vi-VN', { timeStyle: 'short' }).format(
                            new Date(participant.joined_at),
                          )}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 text-[12px] text-primary-dark font-medium">
                        <CheckCircle className="size-4 text-primary" /> Đã gửi sở thích
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteParticipant(participant.id)}
                        className="flex size-8 items-center justify-center rounded-full text-ink-variant hover:text-destructive hover:bg-destructive/10 transition-colors"
                        title="Xóa người tham gia"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </div>

                  {/* Preferences chips list */}
                  <div className="border-t border-hairline/60 pt-3">
                    {participant.preferences.length === 0 ? (
                      <p className="text-[13px] text-ink-variant italic">Không khai báo sở thích ăn uống đặc biệt.</p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {participant.preferences.map((pref) => (
                          <div
                            key={pref.id}
                            className={`inline-flex items-center border rounded-full px-3 py-1 text-[12px] font-bold ${getPreferenceBadgeStyle(
                              pref.preference_type,
                            )}`}
                          >
                            <span className="mr-1.5 opacity-80 uppercase text-[9px] px-1 bg-black/5 rounded">
                              {getPreferenceTypeLabel(pref.preference_type)}
                            </span>
                            <span className="capitalize">{pref.code.replace(/_/g, ' ')}</span>
                            {pref.intensity !== null && (
                              <span className="ml-1 opacity-80 text-[10px]">
                                ({pref.intensity}/5)
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen QR Modal Overlay */}
      {isFullscreenQr && qrDataUrl && (
        <div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90 p-4 font-sans animate-fade-in"
          onClick={() => setIsFullscreenQr(false)}
        >
          <div
            className="flex w-full max-w-[500px] flex-col items-center gap-6 rounded-[24px] bg-white p-8 text-center shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col gap-1">
              <h3 className="text-[24px] font-bold text-primary-dark">
                {t('dining.scanQrPrompt')}
              </h3>
              <p className="text-[14px] text-ink-variant max-w-[360px]">
                {t('dining.scanQrDesc')}
              </p>
            </div>

            <img
              src={qrDataUrl}
              alt="Dining Session Fullscreen QR Code"
              className="w-full aspect-square max-w-[360px] rounded-[16px] border border-hairline shadow-inner"
            />

            <Button
              onClick={() => setIsFullscreenQr(false)}
              className="h-11 px-8 bg-primary-dark text-white rounded-full font-bold flex items-center gap-1.5 hover:bg-primary-dark/90"
            >
              <Minimize2 className="size-4" />
              {t('dining.closeFullscreen')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
