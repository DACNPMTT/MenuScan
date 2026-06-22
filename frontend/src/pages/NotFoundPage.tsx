import { Link } from 'react-router-dom'
import { Button } from '@/shared/components/Button'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function NotFoundPage() {
  useDocumentTitle('Page not found | MenuScan')

  return (
    <main className="not-found-page" aria-labelledby="not-found-title">
      <p className="eyebrow">404</p>
      <h1 id="not-found-title">Page not found</h1>
      <p>The route you opened does not exist in the MenuScan frontend.</p>
      <Button as="link" to="/">
        Back home
      </Button>
      <Link className="text-link" to="/app">
        Open app shell
      </Link>
    </main>
  )
}
