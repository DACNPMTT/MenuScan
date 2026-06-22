import { Link, Outlet } from 'react-router-dom'
import { Button } from '@/shared/components/Button'

export function PublicLayout() {
  return (
    <div className="public-layout">
      <header className="public-layout__header">
        <Link className="brand-link" to="/" aria-label="MenuScan home">
          <span className="brand-link__mark">MS</span>
          <span>MenuScan</span>
        </Link>
        <nav className="public-layout__nav" aria-label="Public navigation">
          <Button as="link" variant="secondary" to="/auth/verify">
            Magic Link
          </Button>
          <Button as="link" to="/app">
            Open app
          </Button>
        </nav>
      </header>
      <main className="public-layout__main">
        <Outlet />
      </main>
    </div>
  )
}
