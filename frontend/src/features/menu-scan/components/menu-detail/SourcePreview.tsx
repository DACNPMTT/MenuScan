import { useEffect, useState } from 'react'
import { FileText, ImageIcon, Loader2 } from 'lucide-react'
import { getAccessToken, refreshAccessToken } from '@/shared/lib/auth-token'
import { API_BASE_URL } from '@/features/menu-scan/lib'
import type { MenuDetail } from '@/features/menu-scan/types'

export interface SourcePreviewProps {
  source: MenuDetail['source']
  accessToken: string | null
}

/** Fetches the original menu file (image or PDF) with auth and renders a
 * preview, refreshing the access token once on 401/403. */
export function SourcePreview({ source, accessToken }: SourcePreviewProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState(false)
  const isImage = source.mime_type.startsWith('image/')
  const isPdf = source.mime_type === 'application/pdf'

  useEffect(() => {
    let active = true
    let nextObjectUrl: string | null = null

    const fetchPreview = async (previewUrl: string, token: string | null) =>
      fetch(previewUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
      })

    const loadPreview = async () => {
      setPreviewError(false)
      setObjectUrl(null)
      try {
        const previewUrl = source.preview_url.startsWith('http')
          ? source.preview_url
          : `${API_BASE_URL}${source.preview_url}`
        const token = getAccessToken() ?? accessToken
        let response = await fetchPreview(previewUrl, token)
        if (response.status === 401 || response.status === 403) {
          const freshToken = await refreshAccessToken()
          if (freshToken) response = await fetchPreview(previewUrl, freshToken)
        }
        if (!response.ok) throw new Error('Preview request failed')
        const blob = await response.blob()
        nextObjectUrl = URL.createObjectURL(blob)
        if (active) {
          setObjectUrl(nextObjectUrl)
        } else {
          URL.revokeObjectURL(nextObjectUrl)
        }
      } catch {
        if (active) setPreviewError(true)
      }
    }

    void loadPreview()
    return () => {
      active = false
      if (nextObjectUrl) URL.revokeObjectURL(nextObjectUrl)
    }
  }, [accessToken, source.preview_url])

  return (
    <section className="mb-6 grid gap-4 rounded-[8px] border border-hairline bg-canvas p-4 lg:grid-cols-[300px_minmax(0,1fr)]">
      <div className="flex min-h-[220px] items-center justify-center overflow-hidden rounded-[8px] border border-hairline bg-surface-muted">
        {objectUrl && isImage ? (
          <img
            src={objectUrl}
            alt={source.file_name}
            className="h-full max-h-[360px] w-full object-contain"
          />
        ) : objectUrl && isPdf ? (
          <iframe
            title={source.file_name}
            src={objectUrl}
            className="h-[360px] w-full border-0"
          />
        ) : previewError ? (
          <div className="flex flex-col items-center gap-2 text-center text-[13px] text-ink-variant">
            <FileText className="size-7" aria-hidden />
            Không thể tải ảnh gốc.
          </div>
        ) : (
          <Loader2 className="size-6 animate-spin text-primary-dark" aria-hidden />
        )}
      </div>
      <div className="flex min-w-0 flex-col justify-center gap-3">
        <div className="flex items-center gap-2 text-primary-dark">
          <ImageIcon className="size-5" aria-hidden />
          <h2 className="mb-0 text-[18px] font-bold">Ảnh menu gốc</h2>
        </div>
        <p className="mb-0 truncate text-[14px] text-ink-variant">
          {source.file_name}
        </p>
        <p className="mb-0 text-[13px] text-ink-variant/70">
          {source.mime_type} · {(source.file_size / 1024).toFixed(1)} KB
        </p>
      </div>
    </section>
  )
}
