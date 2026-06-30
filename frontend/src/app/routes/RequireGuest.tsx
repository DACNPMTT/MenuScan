import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { Spinner } from '@/shared/components/Spinner'

/**
 * Guard for guest-only (pre-auth) routes. An authenticated user is redirected
 * to the app; while auth state is still loading we show a spinner instead of a
 * premature redirect. Used only for the pre-auth transition pages (login,
 * register, check-email) — `auth/verify` establishes the session itself and
 * `auth/set-password` runs after the user is already authenticated, so neither
 * is wrapped here.
 */
export function RequireGuest({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex h-dvh w-screen items-center justify-center bg-app-bg">
        <Spinner />
      </div>
    )
  }
  if (user) return <Navigate to="/app" replace />
  return <>{children}</>
}
