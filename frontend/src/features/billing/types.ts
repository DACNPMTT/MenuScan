// Client-side types for the billing domain (`/api/v1/bills`).
//
// Money fields are always serialized by the backend as decimal strings
// (NUMERIC(14,2)) to avoid precision loss — never parse these into floats
// for arithmetic; convert with `Number()` only at the formatting boundary.

export type BillStatus = 'DRAFT' | 'FINALIZED'

export type BillAdjustmentType =
  | 'DISCOUNT'
  | 'SURCHARGE'
  | 'TAX'
  | 'SERVICE_CHARGE'
  | 'ROUNDING'

export type BillAdjustmentCalculationType = 'FIXED' | 'PERCENTAGE'

export const ADJUSTMENT_TYPE_LABELS = {
  DISCOUNT: 'Giảm giá',
  SURCHARGE: 'Phụ thu',
  TAX: 'Thuế',
  SERVICE_CHARGE: 'Phí dịch vụ',
  ROUNDING: 'Làm tròn',
} satisfies Record<BillAdjustmentType, string>

/** One immutable line item on a bill. `name_snapshot` / `unit_price_snapshot`
 * are fixed at add-time so later menu edits never change a billed amount. */
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

/** A fee/tax/discount line on a bill. `calculated_amount` is signed
 * (negative for discounts) and always server-derived. */
export interface BillAdjustmentResponse {
  id: string
  type: BillAdjustmentType
  calculation_type: BillAdjustmentCalculationType
  label: string
  value: string
  calculated_amount: string
  created_at: string
}

/** Full bill — `data` envelope of every `/bills` response. */
export interface Bill {
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

export type BillResponse = Bill

/** `POST /bills` request body. */
export interface CreateBillRequest {
  menu_id: string
}

export interface BillItemInput {
  food_item_id: string
  quantity: number
}

/** `PATCH /bills/{id}/items` request body — the desired end state. */
export interface UpdateBillItemsRequest {
  items: BillItemInput[]
}

/** `POST/PATCH /bills/{id}/adjustments` request body. */
export interface AdjustmentInput {
  type: BillAdjustmentType
  calculation_type: BillAdjustmentCalculationType
  label: string
  value: string
}

/** Result of `POST /bills/{id}/split`. `shares` sums exactly to
 * `total_amount`; the backend floors each share and distributes the
 * remainder cents to the first people, so no money is lost to rounding. */
export interface BillSplit {
  bill_id: string
  currency: string
  total_amount: string
  people_count: number
  base_share: string
  remainder_units: number
  shares: { person: number; amount: string }[]
}

/** `POST /bills/{id}/split` request body. */
export interface SplitBillRequest {
  people_count: number
}
