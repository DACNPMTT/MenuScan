import { Alert } from '@/shared/components/Alert'
import { Card } from '@/shared/components/Card'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function MenusPage() {
  useDocumentTitle('Menus | MenuScan')

  return (
    <section className="route-page" aria-labelledby="menus-title">
      <p className="eyebrow">Saved menus</p>
      <h1 id="menus-title">Menus</h1>
      <p>
        This route reserves the authenticated menu review area without adding
        backend assumptions ahead of the scan workflow.
      </p>
      <Card>
        <Alert title="No menus yet" variant="warning">
          Menu data will appear here after the scan and review tasks connect to
          the backend API.
        </Alert>
      </Card>
    </section>
  )
}
