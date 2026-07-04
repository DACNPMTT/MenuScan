import { AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'

interface RouteErrorFallbackProps {
  error: Error
  onReset: () => void
}

/** Route-level fallback: rendered inside the authenticated shell (header and
 * footer stay visible). The page content failed, so the user keeps navigation
 * and a reload to recover the broken route. */
export function RouteErrorFallback({ error, onReset }: RouteErrorFallbackProps) {
  void onReset
  return (
    <div className="mx-auto flex w-full max-w-[640px] flex-col items-center gap-5 px-4 py-[60px] text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="size-7 text-destructive" aria-hidden />
      </span>
      <div className="flex flex-col gap-2">
        <h1 className="text-[22px] font-bold leading-[28px] text-primary-dark">
          Trang này gặp lỗi
        </h1>
        <p className="max-w-[420px] text-[14px] text-ink-variant">
          Nội dung không tải được do lỗi bất ngờ. Tải lại trang để thử lại, hoặc
          quay lại Dashboard để tiếp tục.
        </p>
      </div>
      <div className="flex flex-col items-center gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="flex min-h-10 items-center justify-center rounded-[8px] bg-primary-dark px-6 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
        >
          Tải lại trang
        </button>
        <Link
          to="/app"
          className="flex min-h-10 items-center justify-center rounded-[8px] border border-hairline bg-canvas px-6 text-[14px] font-bold text-ink transition-colors hover:bg-surface-muted"
        >
          Về Dashboard
        </Link>
      </div>
      {import.meta.env.DEV && (
        <p className="mt-2 max-w-[600px] break-words rounded-[6px] bg-surface-muted px-3 py-2 text-left font-mono text-[12px] text-destructive">
          {error.message}
        </p>
      )}
    </div>
  )
}
