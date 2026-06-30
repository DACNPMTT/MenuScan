import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { UploadPanel } from '@/features/menu-scan/components/UploadPanel'

export function ScanPage() {
  return (
    <div className="mx-auto w-full max-w-[1100px] px-4 py-[30px] sm:px-[50px] sm:py-[50px]">
      <div className="flex flex-col gap-5">
        <Link
          to="/app"
          className="flex w-fit items-center gap-2 text-[14px] text-ink-variant transition-colors hover:text-primary-dark"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Về Dashboard
        </Link>
        <h1 className="text-[48px] font-bold leading-[56px] tracking-[-0.5px] text-primary-dark">
          Thêm menu
        </h1>
      </div>
      <div className="mt-[40px]">
        <UploadPanel />
      </div>
    </div>
  )
}
