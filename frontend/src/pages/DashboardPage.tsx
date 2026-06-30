import { Link } from 'react-router-dom'
import { Camera, FileUp, ScanLine, Sparkles } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

/**
 * Dashboard. Per the Figma (node 5:970): welcome + system status, quick-action
 * bento, a metrics row and a recent-sessions list.
 *
 * The MVP API contract (doc/content/api-endpoints.md) has no list/aggregate
 * endpoint for scans — only POST /scans and GET /scans/{id}. So metrics and
 * the recent list render an honest empty state rather than fabricated numbers;
 * they wire up once a collection endpoint lands.
 */
export function DashboardPage() {
  useDocumentTitle('Dashboard | MenuScan')
  const { user } = useAuth()
  const displayName = user?.display_name || user?.email?.split('@')[0] || 'bạn'

  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-[30px] sm:px-[50px] sm:py-[40px]">
      {/* Welcome + system status */}
      <div className="flex flex-col gap-2">
        <h1 className="text-[32px] font-bold leading-[40px] tracking-[-0.5px] text-primary-dark sm:text-[44px] sm:leading-[52px]">
          Chào mừng trở lại, {displayName}
        </h1>
        <p className="flex items-center gap-2 text-[14px] text-ink-variant">
          <Sparkles className="size-4 text-primary-dark" aria-hidden />
          Trạng thái hệ thống: mọi dịch vụ đang hoạt động
        </p>
      </div>

      {/* Quick actions */}
      <div className="mt-[30px] grid grid-cols-1 gap-[20px] sm:grid-cols-2">
        <Link
          to="/app/scan"
          className="group flex min-h-[160px] flex-col items-center justify-center gap-4 rounded-[12px] border border-hairline bg-canvas p-[30px] text-center transition-colors hover:bg-surface-muted"
        >
          <span className="flex size-12 items-center justify-center rounded-full bg-primary-dark">
            <FileUp className="size-6 text-white" aria-hidden />
          </span>
          <span className="flex flex-col gap-1.5">
            <span className="text-[20px] leading-[28px] text-primary-dark">
              Tải ảnh / PDF lên
            </span>
            <span className="text-[14px] text-ink-variant">
              Kéo thả hoặc chọn file từ máy
            </span>
          </span>
        </Link>
        <Link
          to="/app/scan/camera"
          className="group flex min-h-[160px] flex-col items-center justify-center gap-4 rounded-[12px] border border-primary-dark bg-primary-dark p-[30px] text-center transition-opacity hover:opacity-90"
        >
          <span className="flex size-12 items-center justify-center rounded-full bg-white">
            <Camera className="size-6 text-primary-dark" aria-hidden />
          </span>
          <span className="flex flex-col gap-1.5">
            <span className="text-[20px] leading-[28px] text-white">
              Quét bằng camera
            </span>
            <span className="text-[14px] text-[#e0e4d6]">
              Chụp menu vật lý tức thì
            </span>
          </span>
        </Link>
      </div>

      {/* Metrics (empty until a scan aggregate endpoint exists). */}
      <div className="mt-[25px] grid grid-cols-1 gap-[20px] sm:grid-cols-3">
        <MetricCard label="Menu đã quét" value="0" />
        <MetricCard label="Món đã trích xuất" value="0" />
        <MetricCard label="Thời gian trung bình" value="—" />
      </div>

      {/* Recent sessions — empty state. */}
      <section className="mt-[30px] overflow-hidden rounded-[12px] border border-hairline bg-canvas">
        <header className="border-b border-hairline bg-app-bg px-[20px] py-[16px]">
          <h2 className="text-[20px] leading-[28px] text-primary-dark">
            Phiên quét gần đây
          </h2>
        </header>
        <div className="flex flex-col items-center gap-4 px-[20px] py-[50px] text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-surface-muted">
            <ScanLine className="size-7 text-primary-dark" aria-hidden />
          </span>
          <div className="flex flex-col gap-1.5">
            <p className="text-[16px] font-medium text-ink">Chưa có phiên quét nào</p>
            <p className="max-w-[320px] text-[14px] text-ink-variant">
              Tải lên menu đầu tiên của bạn để MenuScan trích xuất danh sách món.
            </p>
          </div>
          <Link
            to="/app/scan"
            className="mt-1 rounded-[8px] bg-primary-dark px-[24px] py-[10px] text-[15px] font-bold text-white transition-opacity hover:opacity-90"
          >
            Quét menu ngay
          </Link>
        </div>
      </section>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[12px] border border-hairline bg-canvas px-[21px] py-[20px]">
      <p className="pb-1.5 text-[14px] text-ink-variant">{label}</p>
      <p className="text-[30px] font-bold leading-[34px] text-primary-dark">{value}</p>
    </div>
  )
}
