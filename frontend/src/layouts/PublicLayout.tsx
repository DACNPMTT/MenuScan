import { Link, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/Button'
import { LanguageSwitcher } from '@/shared/components/LanguageSwitcher'
import { useAuth } from '@/app/providers/AuthProvider'

export function PublicLayout() {
  const { user, loading } = useAuth()
  const { t } = useTranslation()

  return (
    <div className="public-layout">
      <header className="public-layout__header">
        <Link to="/" aria-label="MenuScan home" style={{ textDecoration: 'none' }}>
          <span style={{ color: '#3F7A1A', fontWeight: 700, fontSize: '22px', letterSpacing: 0 }}>MenuScan</span>
        </Link>
        <nav className="public-layout__nav" aria-label="Public navigation">
          <LanguageSwitcher />
          {!loading && user ? (
            <>
              <span style={{ fontSize: '0.9rem', marginRight: '8px', opacity: 0.8 }} className="desktop-only">
                {user.email}
              </span>
              <Button as="link" to="/app">
                {t('common.enterApp')}
              </Button>
            </>
          ) : (
            <>
              <Button as="link" variant="secondary" to="/auth/login">
                {t('common.login')}
              </Button>
            </>
          )}
        </nav>
      </header>
      <main className="public-layout__main">
        <Outlet />
      </main>
    </div>
  )
}
