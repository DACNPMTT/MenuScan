import { NavLink, Outlet, Navigate } from 'react-router-dom'
import { LayoutDashboard, ScanLine, Utensils } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { Spinner } from '@/shared/components/Spinner'
import { ErrorBoundary } from '@/shared/components/ErrorBoundary'
import { RouteErrorFallback } from '@/shared/components/RouteErrorFallback'

// Authenticated app shell matching the MenuScan Figma: a top header (logo +
// primary nav + account actions) and a footer. No left sidebar.
const navigationItems = [
  { label: 'Dashboard', to: '/app', icon: LayoutDashboard },
  { label: 'Scan', to: '/app/scan', icon: ScanLine },
  { label: 'Menus', to: '/app/menus', icon: Utensils },
]

export function AuthenticatedLayout() {
  const { user, loading, logout } = useAuth()

  if (loading) {
    return (
      <div className="flex h-dvh w-screen items-center justify-center bg-app-bg">
        <Spinner />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/auth/login" replace />
  }

  return (
    <div className="flex min-h-dvh flex-col bg-app-bg">
      <header className="flex h-[60px] shrink-0 items-center justify-between gap-3 border-b border-hairline bg-canvas px-4 sm:h-[75px] sm:gap-6 sm:px-[50px]">
        <NavLink
          to="/app"
          aria-label="MenuScan app"
          className="shrink-0 text-[22px] font-bold leading-none text-primary-dark sm:text-[30px]"
        >
          MenuScan
        </NavLink>
        <nav
          className="hidden items-center gap-[24px] sm:flex sm:gap-[30px]"
          aria-label="App navigation"
        >
          {navigationItems.map((item) => (
            <NavLink
              end={item.to === '/app'}
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive
                  ? 'text-[15px] font-bold text-primary-dark'
                  : 'text-[15px] font-medium text-ink-variant transition-colors hover:text-primary-dark'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-4">
          <span
            className="hidden max-w-[220px] truncate text-[14px] text-ink-variant md:inline"
            title={user.email}
          >
            {user.email}
          </span>
          <button
            type="button"
            onClick={() => logout()}
            className="rounded-[4px] bg-primary-dark px-[20px] py-[8px] text-[15px] font-bold text-white transition-opacity hover:opacity-90"
          >
            Đăng xuất
          </button>
        </div>
      </header>
      <nav
        className="grid shrink-0 grid-cols-3 border-b border-hairline bg-canvas px-2 py-1.5 sm:hidden"
        aria-label="App navigation"
      >
        {navigationItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              end={item.to === '/app'}
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  'flex min-h-12 flex-col items-center justify-center gap-1 rounded-[8px] px-2 text-[12px] font-semibold transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary-dark'
                    : 'text-ink-variant hover:bg-surface-muted hover:text-primary-dark',
                ].join(' ')
              }
            >
              <Icon className="size-4" aria-hidden />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
      <main className="min-w-0 flex-1">
        <ErrorBoundary fallback={(error, reset) => <RouteErrorFallback error={error} onReset={reset} />}>
          <Outlet />
        </ErrorBoundary>
      </main>

      <footer className="flex shrink-0 flex-col items-center gap-2 border-t border-hairline bg-surface-muted px-4 py-[20px] text-center sm:flex-row sm:justify-between sm:gap-3 sm:px-[50px] sm:py-[30px] sm:text-left">
        <span className="text-[20px] font-bold leading-none text-primary-dark">
          MenuScan
        </span>
        <span className="text-[14px] text-ink-variant">
          © 2024 MenuScan. All rights reserved.
        </span>
      </footer>
    </div>
  )
}
