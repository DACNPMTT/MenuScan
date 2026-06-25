import { NavLink, Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { Spinner } from '@/shared/components/Spinner'

const navigationItems = [
  { label: 'Dashboard', to: '/app' },
  { label: 'Scan', to: '/app/scan' },
  { label: 'Menus', to: '/app/menus' },
]

export function AuthenticatedLayout() {
  const { user, loading, logout } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center' }}>
        <Spinner />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/auth/login" replace />
  }

  return (
    <div className="authenticated-layout">
      <aside className="authenticated-layout__sidebar">
        <NavLink className="brand-link" to="/app" aria-label="MenuScan app">
          <span className="brand-link__mark">MS</span>
          <span>MenuScan</span>
        </NavLink>
        <nav className="authenticated-layout__nav" aria-label="App navigation">
          {navigationItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? 'app-nav-link app-nav-link--active' : 'app-nav-link'
              }
              end={item.to === '/app'}
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div style={{ marginTop: 'auto' }}>
          <div style={{ marginBottom: '12px', fontSize: '0.85rem', color: 'var(--color-text-main)', opacity: 0.7, wordBreak: 'break-all' }}>
            {user.email}
          </div>
          <button
            onClick={() => logout()}
            className="button button--secondary"
            style={{ width: '100%', minHeight: '36px', height: '36px' }}
          >
            Đăng xuất
          </button>
        </div>
      </aside>
      <main className="authenticated-layout__main">
        <Outlet />
      </main>
    </div>
  )
}
