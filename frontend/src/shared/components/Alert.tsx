import type { PropsWithChildren } from 'react'
import { cn } from '@/shared/lib/cn'

type AlertVariant = 'info' | 'success' | 'warning' | 'error'

type AlertProps = PropsWithChildren<{
  title: string
  variant?: AlertVariant
}>

const alertLabels: Record<AlertVariant, string> = {
  error: 'Error',
  info: 'Information',
  success: 'Success',
  warning: 'Warning',
}

export function Alert({ children, title, variant = 'info' }: AlertProps) {
  return (
    <section
      aria-label={alertLabels[variant]}
      className={cn('alert', `alert--${variant}`)}
      role={variant === 'error' ? 'alert' : 'status'}
    >
      <strong className="alert__title">{title}</strong>
      <div className="alert__body">{children}</div>
    </section>
  )
}
