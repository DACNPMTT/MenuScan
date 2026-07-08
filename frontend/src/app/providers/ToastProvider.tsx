/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  ToastViewport,
  type ToastData,
  type ToastVariant,
} from '@/shared/components/ui/toast'

const DEFAULT_DURATION_MS = 5000

export interface ShowToastInput {
  variant: ToastVariant
  title: string
  description?: string
  /** Override the auto-dismiss delay. Ignored for `error` (never auto-dismissed). */
  duration?: number
}

interface ToastContextValue {
  show: (input: ShowToastInput) => string
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

function createToastId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  // Fallback for older runtimes; crypto.randomUUID is ubiquitous on evergreen
  // browsers but we stay defensive for embedded webviews.
  return Math.random().toString(36).slice(2)
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([])
  // Track per-toast timers so we can cancel a pending auto-dismiss when the
  // user closes manually or when a toast is replaced.
  const timers = useRef<Map<string, number>>(new Map())

  const clearTimer = useCallback((id: string) => {
    const timer = timers.current.get(id)
    if (timer !== undefined) {
      window.clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const dismiss = useCallback(
    (id: string) => {
      clearTimer(id)
      setToasts((current) => current.filter((toast) => toast.id !== id))
    },
    [clearTimer],
  )

  const show = useCallback(
    (input: ShowToastInput) => {
      const id = createToastId()
      const toast: ToastData = {
        id,
        variant: input.variant,
        title: input.title,
        description: input.description,
      }
      setToasts((current) => [...current, toast])

      // Error toasts never auto-dismiss: they signal something the user must
      // acknowledge or fix, so silently removing them would hide the problem.
      if (input.variant !== 'error') {
        const delay = input.duration ?? DEFAULT_DURATION_MS
        const timer = window.setTimeout(() => dismiss(id), delay)
        timers.current.set(id, timer)
      }
      return id
    },
    [dismiss],
  )

  const value = useMemo<ToastContextValue>(() => ({ show, dismiss }), [show, dismiss])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
