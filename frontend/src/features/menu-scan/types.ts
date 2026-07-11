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
export interface ScanError {
  code: string
  message: string
}

export interface ScanDetail {
  id: string
  status: ScanStatus
  stage?: ScanStage
  progress: number
  error: ScanError | string | null
  created_at: string
  completed_at: string | null
}

export interface ScanHistoryItem {
  id: string
  status: ScanStatus
  created_at: string
  completed_at: string | null
  source: {
    file_name: string
    mime_type: string
    file_size: number
    preview_url: string
  }
  menu: {
    id: string
    title: string
    is_saved: boolean
    item_count: number
  } | null
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface MenuSavedState {
  id: string
  is_saved: boolean
  updated_at: string
}

export type MenuStatus = 'DRAFT' | 'CONFIRMED'

export interface MenuSource {
  scan_id: string
  file_name: string
  mime_type: string
  file_size: number
  preview_url: string
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
  allergens: string[]
  dietary_tags: string[]
  confidence_score: number | string | null
  sort_order: number
  recommendation?: RecommendationResult | null
}

export interface ParticipantBreakdown {
  display_name: string
  verdict: 'RECOMMENDED' | 'OK' | 'CAUTION' | 'AVOID'
  score?: number | null
  explanation?: string | null
  fit_reasons?: string[]
  risk_reasons?: string[]
}

export interface RecommendationResult {
  verdict: 'RECOMMENDED' | 'OK' | 'CAUTION' | 'AVOID'
  score?: number | null
  explanation?: string | null
  why_suitable?: string | null
  why_not_suitable?: string | null
  suggested_for?: string[]
  warning_for?: string[]
  participant_breakdowns?: ParticipantBreakdown[]
}

export interface MenuSummary {
  id: string
  title: string
  status: MenuStatus
  is_saved: boolean
  item_count: number
  default_currency: string | null
  source: MenuSource
  created_at: string
  updated_at: string
  confirmed_at: string | null
}

export interface MenuDetail extends MenuSummary {
  source_language: string | null
  target_language: string
  items: MenuItemResult[]
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
    status?: MenuStatus
    default_currency: string | null
    is_saved: boolean
    items: MenuItemResult[]
  } | null
}

/** Editable form state for a single menu item (MenuDetailPage editor). */
export interface ItemDraft {
  original_name: string
  translated_name: string
  original_description: string
  translated_description: string
  price: string
  currency: string
  category: string
}

export interface ItemValidationErrors {
  original_name?: string
  price?: string
}

/** Per-item bill line state on the MenuDetail page. */
export interface BillLineState {
  quantity: number
  note: string
}

/** Convenience alias for a menu item used in the bill/editor view. */
export type BillItem = MenuItemResult
