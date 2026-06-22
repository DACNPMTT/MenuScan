import { UploadPanel } from '@/features/menu-scan/components/UploadPanel'
import { useDocumentTitle } from '@/shared/hooks/useDocumentTitle'

export function ScanPage() {
  useDocumentTitle('Scan menu | MenuScan')

  return (
    <section className="route-page" aria-labelledby="scan-title">
      <p className="eyebrow">Menu scan</p>
      <h1 id="scan-title">Scan a menu</h1>
      <p>
        The upload surface is ready for API integration while staying inside
        the menu-scan feature boundary.
      </p>
      <UploadPanel />
    </section>
  )
}
