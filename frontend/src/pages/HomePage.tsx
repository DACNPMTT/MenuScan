import { UploadPanel } from '@/features/menu-scan/components/UploadPanel'
import { AppShell } from '@/layouts/AppShell'
import { StatCard } from '@/shared/components/StatCard'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

const stats = [
  { label: 'Menus scanned', value: '128' },
  { label: 'Avg. processing', value: '14s' },
  { label: 'Items extracted', value: '2.4k' },
]

export function HomePage() {
  useDocumentTitle('MenuScan')

  return (
    <AppShell>
      <section className="home-page" aria-labelledby="home-title">
        <div className="home-page__intro">
          <p className="eyebrow">Restaurant menu intelligence</p>
          <h1 id="home-title">Turn menu photos into structured data.</h1>
          <p>
            A clean React foundation for uploading menus, extracting dishes, and
            reviewing results as the product grows.
          </p>
        </div>

        <UploadPanel />

        <div className="home-page__stats" aria-label="Product stats">
          {stats.map((stat) => (
            <StatCard key={stat.label} label={stat.label} value={stat.value} />
          ))}
        </div>
      </section>
    </AppShell>
  )
}
