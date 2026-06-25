import { Link, Outlet } from 'react-router-dom'
import { Button } from '@/shared/components/Button'
import { useAuth } from '@/app/providers/AuthProvider'

export function PublicLayout() {
  const { user, loading } = useAuth()

  return (
    <div className="public-layout">
      <header className="public-layout__header">
        <Link className="brand-link" to="/" aria-label="MenuScan home">
          <span className="brand-link__mark" style={{ background: '#3F7A1A' }}>MS</span>
          <span style={{ color: '#3F7A1A' }}>MenuScan</span>
        </Link>
        <nav className="public-layout__nav" aria-label="Public navigation">
          {!loading && user ? (
            <>
              <span style={{ fontSize: '0.9rem', marginRight: '8px', opacity: 0.8 }} className="desktop-only">
                {user.email}
              </span>
              <Button as="link" to="/app">
                Vào ứng dụng
              </Button>
            </>
          ) : (
            <>
              <Button as="link" variant="secondary" to="/auth/login">
                Đăng nhập
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
