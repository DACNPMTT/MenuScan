import { Alert } from '@/shared/components/Alert'
import { Card } from '@/shared/components/Card'
import { Spinner } from '@/shared/components/Spinner'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function DashboardPage() {
  useDocumentTitle('Dashboard | MenuScan')

  return (
    <section className="route-page" aria-labelledby="dashboard-title">
      <p className="eyebrow">Authenticated layout</p>
      <h1 id="dashboard-title">Dashboard</h1>
      <p>
        A stable app shell for future authenticated MenuScan workflows and
        account-aware scan history.
      </p>
      <div className="dashboard-grid">
        <Card>
          <h2>System status</h2>
          <Alert title="Frontend foundation online" variant="success">
            Routes, layouts, and shared components are wired for the next
            product slices.
          </Alert>
        </Card>
        <Card>
          <h2>Loading state</h2>
          <div className="inline-status">
            <Spinner label="Preparing authenticated workspace" />
            <span>Preparing authenticated workspace</span>
          </div>
        </Card>
      </div>
    </section>
  )
}
