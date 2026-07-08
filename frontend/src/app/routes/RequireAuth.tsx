import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { Spinner } from '@/shared/components/Spinner'

/** Gate for routes that require a signed-in user. Guests are sent to login,
 * remembering where they came from. Scan routes are intentionally NOT wrapped in
 * this — guests can scan without an account. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner />
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/auth/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}
