import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { Card } from '@/shared/components/Card'
import { Input } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import { Alert } from '@/shared/components/Alert'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function SetPasswordPage() {
  useDocumentTitle('Thiết lập mật khẩu | MenuScan')
  const navigate = useNavigate()
  const { user, loading, setPassword } = useAuth()

  // Form state
  const [password, setPasswordInput] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  // Protect route: redirect to login if not authenticated and not loading
  useEffect(() => {
    if (!loading && !user) {
      navigate('/auth/login', { replace: true })
    }
  }, [user, loading, navigate])

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password) {
      setPasswordError('Vui lòng nhập mật khẩu.')
      return
    }
    if (password.length < 6) {
      setPasswordError('Mật khẩu phải chứa ít nhất 6 ký tự.')
      return
    }
    if (password !== confirmPassword) {
      setPasswordError('Mật khẩu xác nhận không khớp.')
      return
    }

    setSavingPassword(true)
    setPasswordError(null)
    try {
      await setPassword(password)
      // Navigate to app dashboard on success
      navigate('/app', { replace: true })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Có lỗi xảy ra khi lưu mật khẩu. Vui lòng thử lại.'
      setPasswordError(message)
    } finally {
      setSavingPassword(false)
    }
  }

  const handleSkipPassword = () => {
    navigate('/app', { replace: true })
  }

  if (loading || !user) {
    return null // Will redirect in useEffect
  }

  return (
    <div className="auth-page-wrapper">
      <Card className="auth-card">
        <div className="auth-logo">
          <span className="auth-logo__mark" style={{ background: '#3F7A1A' }}>MS</span>
          <span className="auth-logo__text" style={{ color: '#3F7A1A' }}>MenuScan</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', margin: '24px 0' }}>
          <div className="auth-success-badge">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 6L9 17L4 12" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h2 className="auth-card__title" style={{ marginTop: '16px', marginBottom: '8px' }}>Email verified successfully!</h2>
          <p className="auth-card__text" style={{ fontSize: '0.95rem', opacity: 0.8, maxWidth: '340px' }}>
            Tài khoản của bạn đã được xác thực thành công. Bạn có thể thiết lập mật khẩu dưới đây để đăng nhập trực tiếp lần sau.
          </p>
        </div>

        {passwordError && (
          <Alert variant="error" title="Lỗi mật khẩu">
            {passwordError}
          </Alert>
        )}

        <form onSubmit={handleSetPassword} className="auth-form">
          <Input
            id="new-password"
            label="Thiết lập mật khẩu mới"
            type="password"
            placeholder="Tối thiểu 6 ký tự"
            value={password}
            onChange={(e) => setPasswordInput(e.target.value)}
            disabled={savingPassword}
            required
          />

          <Input
            id="confirm-password"
            label="Xác nhận mật khẩu mới"
            type="password"
            placeholder="Nhập lại mật khẩu"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={savingPassword}
            required
          />

          <Button
            type="submit"
            className="auth-btn auth-btn--primary"
            disabled={savingPassword}
            style={{ backgroundColor: '#3F7A1A', borderColor: '#2E6930', color: '#fff', marginTop: '16px' }}
          >
            {savingPassword ? 'Đang lưu...' : 'Lưu mật khẩu & Vào Dashboard'}
          </Button>
          
          <button
            type="button"
            className="auth-skip-btn"
            onClick={handleSkipPassword}
            disabled={savingPassword}
          >
            Bỏ qua thiết lập mật khẩu (Skip)
          </button>
        </form>
      </Card>
    </div>
  )
}
