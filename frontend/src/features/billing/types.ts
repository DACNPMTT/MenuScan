// Types mirroring `src/modules/billing/schemas.py` on the backend.
// Money fields are always decimal strings (never float) — see the backend
// module docstring — so every amount here is typed as `string`.

export type BillStatus = 'DRAFT' | 'FINALIZED'

export type BillAdjustmentType =
  | 'DISCOUNT'
  | 'SURCHARGE'
  | 'TAX'
  | 'SERVICE_CHARGE'
  | 'ROUNDING'

export type BillAdjustmentCalculationType = 'FIXED' | 'PERCENTAGE'

export interface BillItemResponse {
  id: string
  food_item_id: string | null
  name_snapshot: string
  unit_price_snapshot: string
  currency: string
  quantity: number
  line_total: string
  sort_order: number
}

export interface BillAdjustmentResponse {
  id: string
  type: BillAdjustmentType
  calculation_type: BillAdjustmentCalculationType
  label: string
  value: string
  calculated_amount: string
  created_at: string
}

export interface BillResponse {
  id: string
  user_id: string
  menu_id: string
  status: BillStatus
  currency: string
  subtotal_amount: string
  adjustment_total: string
  total_amount: string
  note: string | null
  items: BillItemResponse[]
  adjustments: BillAdjustmentResponse[]
  created_at: string
  updated_at: string
  finalized_at: string | null
}

export interface BillItemInput {
  food_item_id: string
  quantity: number
}

export interface AdjustmentInput {
  type: BillAdjustmentType
  calculation_type: BillAdjustmentCalculationType
  label: string
  value: string
}

export const ADJUSTMENT_TYPE_LABELS: Record<BillAdjustmentType, string> = {
  DISCOUNT: 'Giảm giá',
  SURCHARGE: 'Phụ phí',
  TAX: 'Thuế',
  SERVICE_CHARGE: 'Phí dịch vụ',
  ROUNDING: 'Làm tròn',
}