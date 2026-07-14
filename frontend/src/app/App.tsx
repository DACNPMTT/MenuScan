import { useState } from 'react'
import { AppProviders } from '@/app/providers/AppProviders'
import { AppRoutes } from '@/app/routes/AppRoutes'
import { ErrorBoundary } from '@/shared/components/ErrorBoundary'
import { GlobalErrorFallback } from '@/shared/components/GlobalErrorFallback'
import { SplashScreen } from '@/shared/components/SplashScreen'

export function App() {
  const [splashDone, setSplashDone] = useState(false)

  return (
    <AppProviders>
      <ErrorBoundary fallback={(error, reset) => <GlobalErrorFallback error={error} onReset={reset} />}>
        {!splashDone && <SplashScreen onComplete={() => setSplashDone(true)} />}
        {splashDone && <AppRoutes />}
      </ErrorBoundary>
    </AppProviders>
  )
}
