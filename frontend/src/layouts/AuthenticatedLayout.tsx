import { NavLink, Outlet } from 'react-router-dom'

const navigationItems = [
  { label: 'Dashboard', to: '/app' },
  { label: 'Scan', to: '/app/scan' },
  { label: 'Menus', to: '/app/menus' },
]

export function AuthenticatedLayout() {
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
      </aside>
      <main className="authenticated-layout__main">
        <Outlet />
      </main>
    </div>
  )
}
