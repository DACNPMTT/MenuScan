import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, Check } from 'lucide-react'
import { api } from '@/shared/lib/api'
import { Button } from '@/shared/components/ui/button'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

type VerifyStatus = 'verifying' | 'success' | 'error'

export function VerifyPage() {
  useDocumentTitle('Verify | MenuScan')
  const [params] = useSearchParams()
  const token = params.get('token')
  const [status, setStatus] = useState<VerifyStatus>('verifying')
  const strippedRef = useRef(false)

  // Strip the token from the URL immediately after reading it (rule: never leave
  // the raw token in the address bar / history).
  useEffect(() => {
    if (strippedRef.current) return
    strippedRef.current = true
    const url = new URL(window.location.href)
    url.searchParams.delete('token')
    window.history.replaceState(null, '', url.pathname)
  }, [])

  useEffect(() => {
    let active = true
    async function run() {
      if (!token) {
        if (active) setStatus('error')
        return
      }
      try {
        // POST /auth/verify is not implemented in the backend yet; this will
        // resolve to `success` once it exists. Until then it 404s -> error.
        await api('/auth/verify', {
          method: 'POST',
          body: JSON.stringify({ token }),
        })
        if (active) setStatus('success')
      } catch {
        if (active) setStatus('error')
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [token])

  if (status === 'verifying') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-app-bg font-sans">
        <div
          className="size-8 animate-spin rounded-full border-2 border-hairline border-t-primary"
          role="status"
          aria-label="Verifying"
        />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-app-bg px-5 font-sans">
        <div className="flex w-full max-w-[400px] flex-col items-center gap-6 border border-hairline bg-canvas p-[50px] text-center">
          <h1 className="text-[30px] font-bold tracking-[-0.75px] text-primary-dark">
            MenuScan
          </h1>
          <h2 className="text-[24px] text-ink">Verification isn&apos;t available yet</h2>
          <p className="text-[16px] leading-[22px] text-ink-variant">
            Xác thực email chưa được bật ở backend. Vui lòng quay lại sau hoặc liên
            hệ quản trị viên.
          </p>
          <Button
            asChild
            className="h-12 rounded-full bg-primary font-bold text-white hover:bg-primary/90"
          >
            <Link to="/auth/login">Back to login</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-app-bg px-5 py-[95px] font-sans">
      <div className="pointer-events-none absolute -bottom-48 -right-48 size-96 rounded-full bg-primary-dark opacity-5 blur-2xl" />
      <div className="relative flex w-full max-w-[400px] flex-col">
        <div className="flex flex-col items-center gap-[30px] border border-hairline bg-canvas py-[50px]">
          <h1 className="text-center text-[30px] font-bold leading-[34px] tracking-[-0.75px] text-primary-dark">
            MenuScan
          </h1>

          <div className="relative flex size-24 items-center justify-center rounded-full bg-surface-muted">
            <div className="absolute inset-0 rounded-full bg-success-glow opacity-20" />
            <Check className="relative size-10 text-primary" aria-hidden />
          </div>

          <div className="flex flex-col items-center gap-[7px]">
            <h2 className="text-center text-[30px] font-bold leading-[34px] text-ink">
              Email verified
              <br />
              successfully!
            </h2>
            <p className="text-center text-[16px] leading-[22px] text-ink-variant">
              Your account is now fully set up. You can start exploring menus.
            </p>
          </div>

          <Button
            asChild
            className="h-12 rounded-full bg-primary px-[25px] text-[17px] font-bold text-white hover:bg-primary/90"
          >
            <Link to="/auth/login">
              Proceed to Login <ArrowRight className="size-4" aria-hidden />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
