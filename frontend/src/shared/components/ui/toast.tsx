import { type ReactNode } from 'react'
import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/shared/lib/cn'

export type ToastVariant = 'success' | 'error' | 'info'

export interface ToastData {
  id: string
  variant: ToastVariant
  title: string
  description?: string
}

interface ToastProps extends ToastData {
  onDismiss: (id: string) => void
}

const toastIcon: Record<ToastVariant, ReactNode> = {
  success: <CheckCircle2 className="size-5 text-[#256b2b]" aria-hidden />,
  error: <XCircle className="size-5 text-destructive" aria-hidden />,
  info: <Info className="size-5 text-primary-dark" aria-hidden />,
}

const toastAccent: Record<ToastVariant, string> = {
  success: 'border-[#bfd8b5] bg-[#eef6e9]',
  error: 'border-destructive/30 bg-destructive/5',
  info: 'border-hairline bg-canvas',
}

/** A single toast notification. Self-dismissing is handled by the provider;
 * the close button is always available so error toasts (which the provider
 * never auto-dismisses) can still be cleared by the user. */
export function Toast({ id, variant, title, description, onDismiss }: ToastProps) {
  const { t } = useTranslation()
  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      aria-live={variant === 'error' ? 'assertive' : 'polite'}
      className={cn(
        'pointer-events-auto flex w-full items-start gap-3 rounded-[10px] border px-4 py-3 shadow-[0_8px_24px_rgba(24,29,21,0.12)]',
        toastAccent[variant],
      )}
    >
      <span className="mt-0.5 shrink-0">{toastIcon[variant]}</span>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-bold leading-[20px] text-ink">{title}</p>
        {description && (
          <p className="mt-0.5 text-[13px] leading-[18px] text-ink-variant">
            {description}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(id)}
        aria-label={t('toast.closeAria')}
        className="-mr-1 shrink-0 rounded-[4px] p-1 text-ink-variant transition-colors hover:bg-surface-muted hover:text-ink"
      >
        <X className="size-4" aria-hidden />
      </button>
    </div>
  )
}

interface ToastViewportProps {
  toasts: ToastData[]
  onDismiss: (id: string) => void
}

/** Fixed container for the toast stack. New toasts on top, max 5 visible;
 * older toasts are dropped to keep the region glanceable. */
export function ToastViewport({ toasts, onDismiss }: ToastViewportProps) {
  const { t } = useTranslation()
  const visible = toasts.slice(-5)
  return (
    <div
      aria-label={t('toast.regionAria')}
      className="pointer-events-none fixed inset-x-0 top-0 z-[100] flex flex-col items-center gap-2 px-3 py-3 sm:inset-x-auto sm:left-auto sm:right-4 sm:top-4 sm:w-[380px] sm:items-stretch sm:px-0 sm:py-0"
    >
      {visible.map((toast) => (
        <Toast key={toast.id} {...toast} onDismiss={onDismiss} />
      ))}
    </div>
  )
}
