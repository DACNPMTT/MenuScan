import { AppProviders } from '@/app/providers/AppProviders'
import { AppRoutes } from '@/app/routes/AppRoutes'
import { ErrorBoundary } from '@/shared/components/ErrorBoundary'
import { GlobalErrorFallback } from '@/shared/components/GlobalErrorFallback'

export function App() {
  return (
    <AppProviders>
      <ErrorBoundary fallback={(error, reset) => <GlobalErrorFallback error={error} onReset={reset} />}>
        <AppRoutes />
      </ErrorBoundary>
    </AppProviders>
  )
}
