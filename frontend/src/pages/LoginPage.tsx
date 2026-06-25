import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { Card } from '@/shared/components/Card'
import { Input } from '@/shared/components/Input'
import { Button } from '@/shared/components/Button'
import { Alert } from '@/shared/components/Alert'

export function LoginPage() {
  const { user, login, requestMagicLink } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Form states
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isRegisterMode, setIsRegisterMode] = useState(false)
  const [isEmailSent, setIsEmailSent] = useState(false)
  
  // UI states
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  
  // Resend cooldown timer
  const [resendCooldown, setResendCooldown] = useState(0)

  // Redirect to app if already logged in
  useEffect(() => {
    if (user) {
      const origin = (location.state as any)?.from?.pathname || '/app'
      navigate(origin, { replace: true })
    }
  }, [user, navigate, location])

  // Cooldown countdown
  useEffect(() => {
    if (resendCooldown <= 0) return
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [resendCooldown])

  // Toggle modes
  const handleToggleMode = () => {
    setIsRegisterMode(!isRegisterMode)
    setError(null)
    setSuccessMessage(null)
  }

  // Handle traditional password login
  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Vui lòng nhập đầy đủ email và mật khẩu.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await login(email, password)
    } catch (err: any) {
      setError(err.message || 'Email hoặc mật khẩu không chính xác.')
    } finally {
      setLoading(false)
    }
  }

  // Handle Magic Link request (Signup/Passwordless)
  const handleMagicLinkRequest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!email) {
      setError('Vui lòng nhập email để tiếp tục.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await requestMagicLink(email)
      setIsEmailSent(true)
      setResendCooldown(response.resend_after_seconds || 60)
      setSuccessMessage(response.message || 'Liên kết đăng nhập đã được gửi!')
    } catch (err: any) {
      setError(err.message || 'Không thể gửi email. Vui lòng thử lại sau.')
    } finally {
      setLoading(false)
    }
  }

  // Render inbox message screen (Mockup 2)
  if (isEmailSent) {
    return (
      <div className="auth-page-wrapper">
        <Card className="auth-card auth-card--center">
          <div className="auth-logo">
            <span className="auth-logo__mark">MS</span>
            <span className="auth-logo__text">MenuScan</span>
          </div>

          <div className="auth-inbox-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="2" y="4" width="20" height="16" rx="4" fill="#E8F4E5" stroke="#3F7A1A" strokeWidth="2"/>
              <path d="M22 7L13.03 12.7C12.4 13.1 11.6 13.1 10.97 12.7L2 7" stroke="#3F7A1A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="20" cy="6" r="3" fill="#3F7A1A"/>
            </svg>
          </div>

          <h2 className="auth-card__title">Check your inbox!</h2>
          <p className="auth-card__text">
            Chúng tôi đã gửi một liên kết xác thực đến địa chỉ email <strong>{email}</strong>. 
            Vui lòng nhấn vào liên kết trong email để kích hoạt tài khoản của bạn.
          </p>

          <Button
            type="button"
            className="auth-btn auth-btn--primary"
            disabled={loading || resendCooldown > 0}
            onClick={() => handleMagicLinkRequest()}
          >
            {resendCooldown > 0 ? `Gửi lại sau (${resendCooldown}s)` : 'Gửi lại email xác thực'}
          </Button>

          <button 
            type="button" 
            className="auth-back-link"
            onClick={() => {
              setIsEmailSent(false)
              setError(null)
            }}
          >
            Quay lại trang đăng nhập
          </button>
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

        <div className="auth-header">
          <h2 className="auth-card__title">Welcome back</h2>
          <p className="auth-card__subtitle">
            {isRegisterMode ? 'Đăng ký tài khoản mới của bạn' : 'Đăng nhập vào hệ thống MenuScan'}
          </p>
        </div>

        {/* Google Sign In Button */}
        <button 
          type="button" 
          className="google-signin-btn"
          onClick={() => {
            setError('Tính năng đăng nhập với Google hiện chưa khả dụng ở bản MVP.')
          }}
        >
          <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </button>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        {error && (
          <Alert variant="error" title="Lỗi">
            {error}
          </Alert>
        )}

        {successMessage && (
          <Alert variant="success" title="Thành công">
            {successMessage}
          </Alert>
        )}

        {/* Login/Signup Form */}
        <form onSubmit={isRegisterMode ? handleMagicLinkRequest : handlePasswordLogin} className="auth-form">
          <Input
            id="email-input"
            label="Email Address"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
          />

          {!isRegisterMode && (
            <div className="password-field-container">
              <div className="password-input-wrapper">
                <Input
                  id="password-input"
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
              <button
                type="button"
                className="forgot-password-link"
                onClick={() => {
                  setError('Để khôi phục tài khoản, vui lòng chọn "Đăng ký / Đăng nhập không mật khẩu" để nhận Magic Link đăng nhập nhanh.')
                }}
              >
                Forgot password?
              </button>
            </div>
          )}

          <Button
            type="submit"
            className="auth-btn auth-btn--primary"
            disabled={loading}
            style={{ backgroundColor: '#3F7A1A', borderColor: '#2E6930', color: '#fff', marginTop: '12px' }}
          >
            {loading ? 'Đang xử lý...' : (isRegisterMode ? 'Sign Up' : 'Log In')}
          </Button>
        </form>

        <div className="auth-footer">
          <button 
            type="button" 
            className="auth-toggle-btn"
            onClick={handleToggleMode}
          >
            {isRegisterMode ? (
              <>Already have an account? <span className="auth-link-text">Log in</span></>
            ) : (
              <>Don't have an account? <span className="auth-link-text">Sign up</span></>
            )}
          </button>
        </div>
      </Card>
    </div>
  )
}
