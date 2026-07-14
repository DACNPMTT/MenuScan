import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { UploadPanel } from '@/features/menu-scan/components/UploadPanel'
import { useAuth } from '@/app/providers/AuthProvider'
import { PageTransition } from '@/shared/components/motion/PageTransition'
import { Button } from '@/shared/components/ui/button'

export function ScanPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  return (
    <PageTransition className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[50px]">
      <div className="flex flex-col gap-5">
        <Button variant="ghost" size="sm" asChild className="w-fit">
          <Link to={user ? '/app' : '/'}>
            <ArrowLeft className="size-4" aria-hidden />
            {user ? t('common.backToDashboard') : t('common.backToHome')}
          </Link>
        </Button>
        <h1 className="text-[40px] font-bold leading-[48px] text-ink sm:text-[48px] sm:leading-[56px]">
          {t('scan.title')}
        </h1>
      </div>
      <div className="mt-[40px]">
        <UploadPanel />
      </div>
    </PageTransition>
  )
}
