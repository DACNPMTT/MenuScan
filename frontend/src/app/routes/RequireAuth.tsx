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
    // Carry the whole location, not just the path. It holds the router state the
    // page was navigated with — e.g. the "start the enrichment pass" flag set by
    // the scan result's primary button. Reducing it to a string dropped that flag,
    // so a guest who signed in at that exact prompt silently never got enriched.
    return <Navigate to="/auth/login" replace state={{ from: location }} />
  }
  return <>{children}</>
}
