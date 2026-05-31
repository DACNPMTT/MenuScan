import type { PropsWithChildren } from 'react'

const navigationItems = ['Overview', 'Menus', 'Reviews']

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <a className="app-shell__brand" href="/" aria-label="MenuScan home">
          <span className="app-shell__brand-mark">MS</span>
          <span>MenuScan</span>
        </a>
        <nav className="app-shell__nav" aria-label="Primary navigation">
          {navigationItems.map((item) => (
            <a href="/" key={item}>
              {item}
            </a>
          ))}
        </nav>
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  )
}
