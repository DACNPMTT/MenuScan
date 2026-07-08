import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { UploadPanel } from '@/features/menu-scan/components/UploadPanel'
import { useAuth } from '@/app/providers/AuthProvider'

export function ScanPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  return (
    <div className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[50px]">
      <div className="flex flex-col gap-5">
        <Link
          to={user ? '/app' : '/'}
          className="flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary-dark"
        >
          <ArrowLeft className="size-4" aria-hidden />
          {user ? t('common.backToDashboard') : t('common.backToHome')}
        </Link>
        <h1 className="text-[48px] font-bold leading-[56px] tracking-[-0.5px] text-primary-dark">
          {t('scan.title')}
        </h1>
      </div>
      <div className="mt-[40px]">
        <UploadPanel />
      </div>
    </div>
  )
}
