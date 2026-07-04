import { Link } from 'react-router-dom'
import { Button } from '@/shared/components/Button'
import { useAuth } from '@/app/providers/AuthProvider'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function NotFoundPage() {
  useDocumentTitle('Không tìm thấy trang | MenuScan')
  const { user } = useAuth()

  return (
    <main className="not-found-page" aria-labelledby="not-found-title">
      <p className="eyebrow">404</p>
      <h1 id="not-found-title">Không tìm thấy trang</h1>
      <p>Trang bạn mở không tồn tại trong MenuScan.</p>
      {user ? (
        <Button as="link" to="/app">
          Về Dashboard
        </Button>
      ) : (
        <Button as="link" to="/">
          Về trang chủ
        </Button>
      )}
      <Link className="text-link" to="/">
        Trang chủ MenuScan
      </Link>
    </main>
  )
}
