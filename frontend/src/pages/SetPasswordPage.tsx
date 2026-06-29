import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function SetPasswordPage() {
  useDocumentTitle('Thiết lập mật khẩu | MenuScan')
  const navigate = useNavigate()
  const { user, loading, setPassword } = useAuth()

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

  const handleSetPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
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

  if (loading || !user) {
    return null // Will redirect in useEffect
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-5 py-[75px] font-sans">
      <div className="flex w-full max-w-[400px] flex-col">
        <header className="mb-[45px] flex flex-col items-center gap-[18px] text-center">
          <h1 className="text-[30px] font-bold leading-[34px] tracking-[-0.75px] text-primary-dark">
            MenuScan
          </h1>
          <div className="flex size-16 items-center justify-center rounded-full bg-primary">
            <Check className="size-8 text-white" aria-hidden />
          </div>
          <div className="flex flex-col gap-[7px]">
            <p className="text-[20px] leading-[30px] text-ink">
              Email verified successfully!
            </p>
            <p className="text-[15px] leading-[22px] text-ink-variant">
              Thiết lập mật khẩu để đăng nhập trực tiếp lần sau.
            </p>
          </div>
        </header>

        <form onSubmit={handleSetPassword} noValidate className="flex flex-col gap-[30px] pb-4">
          <label className="flex flex-col gap-[5px]">
            <span className="text-[14px] leading-[14px] text-ink">New Password</span>
            <Input
              type="password"
              required
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPasswordInput(event.target.value)}
              placeholder="Minimum 6 characters"
              aria-label="New Password"
              disabled={savingPassword}
              className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
            />
          </label>

          <label className="flex flex-col gap-[5px]">
            <span className="text-[14px] leading-[14px] text-ink">Confirm Password</span>
            <Input
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Re-enter your password"
              aria-label="Confirm Password"
              disabled={savingPassword}
              className="rounded-none border-0 border-b border-hairline bg-transparent px-0 py-1 text-[16px] text-ink shadow-none placeholder:text-placeholder focus-visible:border-primary-dark focus-visible:ring-0"
            />
          </label>

          {passwordError && (
            <p role="alert" className="-mt-4 text-[14px] text-destructive">
              {passwordError}
            </p>
          )}

          <Button
            type="submit"
            disabled={savingPassword}
            className="h-12 rounded-full bg-primary text-[17px] font-bold text-white hover:bg-primary/90"
          >
            {savingPassword ? 'Đang lưu...' : 'Save Password'}
          </Button>
        </form>
      </div>
    </div>
  )
}
