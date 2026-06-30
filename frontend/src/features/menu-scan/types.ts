// Client-side scan file validation and API types.
//
// The backend is the source of truth for upload validation (MVP contract +
// POST /api/v1/scans): exactly one file, <=10 MB, JPG/JPEG/PNG/WEBP/PDF,
// PDF <=5 pages and not password-protected. The constants here mirror the
// contract so we can fail fast in the UI; the server still re-validates.

export type MenuScanStatus = 'ready' | 'uploading' | 'processing' | 'complete'

export const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'pdf'] as const
export type AllowedExtension = (typeof ALLOWED_EXTENSIONS)[number]

export const ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf',
] as const
export type AllowedMimeType = (typeof ALLOWED_MIME_TYPES)[number]

export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB

export interface FileValidationError {
  code: 'UNSUPPORTED_TYPE' | 'FILE_TOO_LARGE'
  message: string
}

export interface SelectedFile {
  file: File
  /** Object URL for image preview; null for PDF (rendered as a file chip). */
  previewUrl: string | null
  error: FileValidationError | null
}

/** `POST /api/v1/scans` success body (`data` envelope). */
export interface ScanSource {
  file_name: string
  mime_type: string
  file_size: number
}

export interface ScanData {
  id: string
  status: string
  progress: number
  source: ScanSource
  target_language: string
  created_at: string
}

export type ScanStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
export type ScanStage = 'UPLOADING' | 'OCR' | 'ANALYZING' | 'TRANSLATING' | 'FINALIZING'

/** `GET /api/v1/scans/{id}` body (`data` envelope). */
export interface ScanDetail {
  id: string
  status: ScanStatus
  stage?: ScanStage
  progress: number
  error: string | null
  created_at: string
  completed_at: string | null
}

export interface MenuItemResult {
  id: string
  original_name: string
  translated_name: string | null
  original_description: string | null
  translated_description: string | null
  price: string | null
  currency: string | null
  category: string | null
  confidence_score: number
  sort_order: number
}

/** `GET /api/v1/scans/{id}/result` body (`data` envelope). */
export interface ScanResult {
  scan: {
    id: string
    status: string
    source: {
      file_name: string
      mime_type: string
      file_size: number
      preview_url: string
    }
    detected_language: string | null
    target_language: string
    processing_time_ms: number | null
  }
  menu: {
    id: string
    title: string | null
    default_currency: string | null
    is_saved: boolean
    items: MenuItemResult[]
  } | null
}
