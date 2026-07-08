import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/shared/components/Button'
import { useAuth } from '@/app/providers/AuthProvider'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function NotFoundPage() {
  const { t } = useTranslation()
  useDocumentTitle(`${t('notFound.title')} | MenuScan`)
  const { user } = useAuth()

  return (
    <main className="not-found-page" aria-labelledby="not-found-title">
      <p className="eyebrow">404</p>
      <h1 id="not-found-title">{t('notFound.title')}</h1>
      <p>{t('notFound.body')}</p>
      {user ? (
        <Button as="link" to="/app">
          {t('notFound.toDashboard')}
        </Button>
      ) : (
        <Button as="link" to="/">
          {t('notFound.toHome')}
        </Button>
      )}
      <Link className="text-link" to="/">
        {t('notFound.home')}
      </Link>
    </main>
  )
}
