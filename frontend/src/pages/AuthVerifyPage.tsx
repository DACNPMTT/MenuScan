import { useEffect, useState, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { Card } from '@/shared/components/Card'
import { Button } from '@/shared/components/Button'
import { Alert } from '@/shared/components/Alert'
import { Spinner } from '@/shared/components/Spinner'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function AuthVerifyPage() {
  useDocumentTitle('Xác thực tài khoản | MenuScan')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { verifyMagicLink } = useAuth()

  const token = searchParams.get('token')

  const [verifying, setVerifying] = useState(!!token)
  const [error, setError] = useState<string | null>(
    token ? null : 'Mã xác thực (token) không tìm thấy trong URL. Vui lòng kiểm tra lại liên kết trong email.'
  )

  const hasRun = useRef(false)

  useEffect(() => {
    if (!token) return

    if (hasRun.current) return
    hasRun.current = true

    const performVerification = async () => {
      try {
        await verifyMagicLink(token)
        // Decoupled transition: navigate to set password page on success
        navigate('/auth/set-password', { replace: true })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Liên kết xác thực đã hết hạn hoặc không hợp lệ.'
        setError(message)
        setVerifying(false)
      }
    }

    performVerification()
  }, [token, verifyMagicLink, navigate])

  if (verifying) {
    return (
      <div className="auth-page-wrapper">
        <Card className="auth-card auth-card--center">
          <div className="auth-logo">
            <span className="auth-logo__mark" style={{ background: '#3F7A1A' }}>MS</span>
            <span className="auth-logo__text" style={{ color: '#3F7A1A' }}>MenuScan</span>
          </div>
          <div style={{ margin: '32px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
            <Spinner />
            <p style={{ margin: 0, fontWeight: 500, color: 'var(--color-text-main)' }}>
              Đang xác thực liên kết đăng nhập của bạn...
            </p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="auth-page-wrapper">
      <Card className="auth-card">
        <div className="auth-logo">
          <span className="auth-logo__mark">MS</span>
          <span className="auth-logo__text">MenuScan</span>
        </div>
        
        <h2 className="auth-card__title" style={{ color: '#ea4335', marginTop: '24px' }}>Xác thực thất bại</h2>
        
        <Alert variant="error" title="Lỗi xác thực">
          {error}
        </Alert>

        <Button
          type="button"
          className="auth-btn auth-btn--primary"
          style={{ marginTop: '24px' }}
          onClick={() => navigate('/auth/login')}
        >
          Quay lại trang đăng nhập
        </Button>
      </Card>
    </div>
  )
}
