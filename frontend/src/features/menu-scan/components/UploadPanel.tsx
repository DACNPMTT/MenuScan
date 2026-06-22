import type { MenuScanStatus } from '@/features/menu-scan/types'
import { Button } from '@/shared/components/Button'
import { Card } from '@/shared/components/Card'

const allowedFormats = ['PNG', 'JPG', 'PDF']
const status: MenuScanStatus = 'ready'

export function UploadPanel() {
  return (
    <Card className="upload-panel" aria-labelledby="upload-title">
      <div>
        <p className="eyebrow">Scan workflow</p>
        <h2 id="upload-title">Upload a menu</h2>
        <p>
          Drop in a menu image or PDF. The extraction flow can plug into this
          feature folder without spreading state across the app.
        </p>
      </div>

      <div className="upload-panel__dropzone">
        <span className="upload-panel__icon" aria-hidden="true">
          +
        </span>
        <div>
          <strong>Choose file</strong>
          <span>{allowedFormats.join(', ')} up to 20MB</span>
        </div>
      </div>

      <div className="upload-panel__footer">
        <span>Status: {status}</span>
        <Button type="button">Start scan</Button>
      </div>
    </Card>
  )
}
