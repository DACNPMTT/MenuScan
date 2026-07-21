import { NavLink, Link, useLocation, useOutlet } from 'react-router-dom'
import {
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Plus,
  ReceiptText,
  ScanLine,
  UserCircle,
  Utensils,
  Users,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'motion/react'
import { useAuth } from '@/app/providers/AuthProvider'
import { Spinner } from '@/shared/components/Spinner'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { MenuScanLogo } from '@/shared/components/mascot/NonLaMark'
import { ErrorBoundary } from '@/shared/components/ErrorBoundary'
import { RouteErrorFallback } from '@/shared/components/RouteErrorFallback'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import { Avatar, AvatarBadge, AvatarFallback } from '@/shared/components/ui/avatar'

// Authenticated app shell: a sticky glass header (logo badge + pill nav with a
// motion active indicator + account actions), a segmented mobile tab bar, and
// a footer. No left sidebar. The <Outlet/> is wrapped in an AnimatePresence so
// in-app page transitions animate while the shell stays mounted.
const navigationItems = [
  { key: 'dashboard', to: '/app', icon: LayoutDashboard, authOnly: true },
  { key: 'scan', to: '/app/scan', icon: ScanLine, authOnly: false },
  { key: 'dining', to: '/app/dining', icon: Users, authOnly: true },
  { key: 'menus', to: '/app/menus', icon: Utensils, authOnly: true },
  { key: 'bills', to: '/app/bills', icon: ReceiptText, authOnly: true },
] as const

const pillSpring = { type: 'spring' as const, stiffness: 380, damping: 30 }

export function AuthenticatedLayout() {
  const { user, loading, logout } = useAuth()
  const { t } = useTranslation()
  const location = useLocation()
  const outlet = useOutlet()
  const accountLabel = user?.display_name || user?.email?.split('@')[0] || t('nav.profile')
  // Avatar fallback: just the first letter of display_name (or email local-part).
  const initial =
    (user?.display_name?.trim()?.[0] || user?.email?.[0] || '?').toUpperCase()
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
      <header className="sticky top-0 z-30 flex min-h-[64px] shrink-0 items-center justify-between gap-2 border-b border-border bg-surface/70 px-3 py-2 backdrop-blur-xl sm:h-[72px] sm:gap-6 sm:px-[50px] sm:py-0">
        <div className="min-w-0">
          <a
            href="/"
            className="flex items-center gap-2.5"
          >
            <span className="flex size-9 items-center justify-center rounded-2xl bg-[#d7ffb8] sm:size-10">
              <MenuScanLogo size={26} />
            </span>
            <span className="block text-[22px] font-extrabold leading-none tracking-tight text-ink sm:text-[26px]">
              MenuScan
            </span>
          </a>
        </div>
        <nav
          className="relative hidden items-center gap-1 rounded-full bg-panel/80 p-1 sm:flex"
          aria-label="App navigation"
        >
          {navItems.map((item) => (
            <NavLink
              end={item.to === '/app'}
              key={item.to}
              to={item.to}
              className="relative rounded-full px-3.5 py-2 text-[14px] font-semibold transition-colors duration-200"
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-full bg-primary shadow-2 shadow-primary/30"
                      transition={pillSpring}
                    />
                  )}
                  <span
                    className={
                      isActive
                        ? 'relative z-10 text-white'
                        : 'relative z-10 text-ink-variant hover:text-primary'
                    }
                  >
                    {t(`nav.${item.key}`)}
                  </span>
                  {isActive && (
                    <motion.span
                      layoutId="nav-dot"
                      className="absolute -bottom-1 left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-accent"
                      transition={pillSpring}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <LanguageSwitcher className="hidden sm:inline-flex" />
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex max-w-[220px] items-center gap-1.5 px-2 text-[14px] font-medium text-ink-variant"
                  title={user.email}
                >
                  <span className="hidden truncate md:inline-block">{accountLabel}</span>
                  <ChevronDown className="hidden size-4 shrink-0 md:inline-block" aria-hidden />
                  {/* Avatar with PlusIcon badge (no image — just first-letter fallback). */}
                  <Avatar>
                    <AvatarFallback>{initial}</AvatarFallback>
                    <AvatarBadge>
                      <Plus aria-hidden />
                    </AvatarBadge>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link to="/app/profile">
                    <UserCircle className="size-4" aria-hidden />
                    {t('nav.profile')}
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => logout()}>
                  <LogOut className="size-4" aria-hidden />
                  {t('common.logout')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild className="h-10 px-5 text-[15px] font-bold">
              <Link to="/auth/login">{t('common.login')}</Link>
            </Button>
          )}
        </div>
      </header>
      <nav
        className="min-w-0 shrink-0 overflow-hidden border-b border-border bg-surface/70 px-3 py-2 backdrop-blur-xl sm:hidden"
        aria-label="App navigation"
      >
        <div className="flex min-w-0 gap-1 rounded-full bg-panel/80 p-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const label = t(`nav.${item.key}`)
            return (
              <NavLink
                end={item.to === '/app'}
                key={item.to}
                to={item.to}
                aria-label={label}
                className={({ isActive }) =>
                  cn(
                    'relative flex min-h-10 min-w-0 items-center justify-center rounded-full text-[12px] font-semibold transition-[flex] duration-200',
                    isActive ? 'flex-[1.75_1_0%] gap-1.5 px-2' : 'flex-1 px-1',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="nav-pill-mobile"
                        className="absolute inset-0 rounded-full bg-primary shadow-2 shadow-primary/30"
                        transition={pillSpring}
                      />
                    )}
                    <Icon
                      className={
                        isActive
                          ? 'relative z-10 size-4 shrink-0 text-white'
                          : 'relative z-10 size-4 shrink-0 text-ink-variant'
                      }
                      aria-hidden
                    />
                    <span
                      className={
                        isActive
                          ? 'relative z-10 min-w-0 truncate text-white'
                          : 'sr-only'
                      }
                    >
                      {label}
                    </span>
                  </>
                )}
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
          <AnimatePresence mode="wait">
            <div key={location.pathname} className="min-h-0">
              {outlet}
            </div>
          </AnimatePresence>
        </ErrorBoundary>
      </main>

      <footer className="flex shrink-0 flex-col items-center gap-3 border-t border-border bg-panel px-4 py-[24px] text-center sm:flex-row sm:justify-between sm:gap-3 sm:px-[50px] sm:py-[28px] sm:text-left">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-xl bg-[#d7ffb8] shadow-1">
            <MenuScanLogo size={22} />
          </span>
          <span className="text-[18px] font-extrabold leading-none tracking-tight text-ink">
            MenuScan
          </span>
        </div>
        <span className="text-[13px] text-ink-variant">
          {t('footer.rights', { year: new Date().getFullYear() })}
        </span>
      </footer>
    </div>
  )
}
