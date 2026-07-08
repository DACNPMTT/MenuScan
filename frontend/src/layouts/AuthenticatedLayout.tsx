import { NavLink, Outlet, Link } from 'react-router-dom'
import { LayoutDashboard, LogOut, ScanLine, Utensils } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { Spinner } from '@/shared/components/Spinner'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { ErrorBoundary } from '@/shared/components/ErrorBoundary'
import { RouteErrorFallback } from '@/shared/components/RouteErrorFallback'

// Authenticated app shell matching the MenuScan Figma: a top header (logo +
// primary nav + account actions) and a footer. No left sidebar.
const navigationItems = [
  { key: 'dashboard', to: '/app', icon: LayoutDashboard, authOnly: true },
  { key: 'scan', to: '/app/scan', icon: ScanLine, authOnly: false },
  { key: 'menus', to: '/app/menus', icon: Utensils, authOnly: true },
] as const

export function AuthenticatedLayout() {
  const { user, loading, logout } = useAuth()
  const { t } = useTranslation()
  const accountLabel = user?.display_name || user?.email?.split('@')[0] || t('nav.profile')
  // The app shell renders for guests too — they can scan without an account.
  // Auth-only nav/actions are hidden for guests, and protected pages guard
  // themselves via RequireAuth.
  const navItems = navigationItems.filter((item) => user || !item.authOnly)

  if (loading) {
    return (
      <div className="flex h-dvh w-screen items-center justify-center bg-app-bg">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh flex-col bg-app-bg">
      <header className="flex min-h-[64px] shrink-0 items-center justify-between gap-2 border-b border-hairline bg-canvas px-3 py-2 sm:h-[75px] sm:gap-6 sm:px-[50px] sm:py-0">
        <div className="min-w-0 shrink">
          <NavLink
            to={user ? '/app' : '/'}
            aria-label="MenuScan app"
            className="block text-primary-dark"
          >
            <span className="block text-[22px] font-bold leading-none sm:text-[30px]">
              MenuScan
            </span>
          </NavLink>
          {user && (
            <NavLink
              to="/app/profile"
              className="mt-1 block max-w-[min(62vw,230px)] truncate text-[12px] font-medium leading-none text-ink-variant transition-colors hover:text-primary-dark sm:hidden"
              title={user.email}
            >
              {accountLabel}
            </NavLink>
          )}
        </div>
        <nav
          className="hidden items-center gap-[24px] sm:flex sm:gap-[30px]"
          aria-label="App navigation"
        >
          {navItems.map((item) => (
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
              {t(`nav.${item.key}`)}
            </NavLink>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-2 sm:gap-4">
          <LanguageSwitcher className="hidden sm:inline-flex" />
          {user ? (
            <>
              <NavLink
                to="/app/profile"
                className="hidden max-w-[220px] truncate text-[14px] text-ink-variant transition-colors hover:text-primary-dark md:inline"
                title={user.email}
              >
                {accountLabel}
              </NavLink>
              <button
                type="button"
                onClick={() => logout()}
                className="flex size-10 items-center justify-center rounded-[8px] bg-primary-dark text-[15px] font-bold text-white transition-opacity hover:opacity-90 sm:size-auto sm:rounded-[4px] sm:px-[20px] sm:py-[8px]"
              >
                <LogOut className="size-4 sm:hidden" aria-hidden />
                <span className="sr-only sm:not-sr-only">{t('common.logout')}</span>
              </button>
            </>
          ) : (
            <Link
              to="/auth/login"
              className="flex items-center justify-center rounded-[4px] bg-primary-dark px-[20px] py-[8px] text-[15px] font-bold text-white transition-opacity hover:opacity-90"
            >
              {t('common.login')}
            </Link>
          )}
        </div>
      </header>
      <nav
        className="shrink-0 border-b border-hairline bg-surface-muted px-3 py-2 sm:hidden"
        aria-label="App navigation"
      >
        <div className="grid grid-cols-3 gap-1 rounded-[10px] bg-canvas p-1">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                end={item.to === '/app'}
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    'flex min-h-11 items-center justify-center gap-1.5 rounded-[8px] px-2 text-[12px] font-semibold transition-colors',
                    isActive
                      ? 'bg-primary-dark text-white shadow-sm'
                      : 'text-ink-variant hover:bg-surface-muted hover:text-primary-dark',
                  ].join(' ')
                }
              >
                <Icon className="size-4 shrink-0" aria-hidden />
                <span className="truncate">{t(`nav.${item.key}`)}</span>
              </NavLink>
            )
          })}
        </div>
        <div className="mt-2 flex justify-center">
          <LanguageSwitcher />
        </div>
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
          {t('footer.rights', { year: 2024 })}
        </span>
      </footer>
    </div>
  )
}
