import { apiRequest } from '@/shared/lib/api'
import type {
  AdjustmentInput,
  BillItemInput,
  BillResponse,
} from '@/features/billing/types'

/** `POST /api/v1/bills` — create an empty DRAFT bill scoped to a menu. */
export function createBill(
  menuId: string,
  token: string | null,
): Promise<BillResponse> {
  return apiRequest<BillResponse>('/api/v1/bills', {
    method: 'POST',
    token: token ?? undefined,
    body: JSON.stringify({ menu_id: menuId }),
  })
}

/** `GET /api/v1/bills/{id}` */
export function getBill(billId: string, token: string | null): Promise<BillResponse> {
  return apiRequest<BillResponse>(`/api/v1/bills/${billId}`, {
    method: 'GET',
    token: token ?? undefined,
  })
}

/**
 * `PATCH /api/v1/bills/{id}/items` — replace the bill's line items with the
 * desired end state (see backend docstring: omit an item to remove it).
 */
export function replaceBillItems(
  billId: string,
  items: BillItemInput[],
  token: string | null,
): Promise<BillResponse> {
  return apiRequest<BillResponse>(`/api/v1/bills/${billId}/items`, {
    method: 'PATCH',
    token: token ?? undefined,
    body: JSON.stringify({ items }),
  })
}

/** `POST /api/v1/bills/{id}/adjustments` */
export function addAdjustment(
  billId: string,
  payload: AdjustmentInput,
  token: string | null,
): Promise<BillResponse> {
  return apiRequest<BillResponse>(`/api/v1/bills/${billId}/adjustments`, {
    method: 'POST',
    token: token ?? undefined,
    body: JSON.stringify(payload),
  })
}

/** `PATCH /api/v1/bills/{id}/adjustments/{adjustmentId}` */
export function updateAdjustment(
  billId: string,
  adjustmentId: string,
  payload: AdjustmentInput,
  token: string | null,
): Promise<BillResponse> {
  return apiRequest<BillResponse>(
    `/api/v1/bills/${billId}/adjustments/${adjustmentId}`,
    {
      method: 'PATCH',
      token: token ?? undefined,
      body: JSON.stringify(payload),
    },
  )
}

/** `DELETE /api/v1/bills/{id}/adjustments/{adjustmentId}` */
export function removeAdjustment(
  billId: string,
  adjustmentId: string,
  token: string | null,
): Promise<BillResponse> {
  return apiRequest<BillResponse>(
    `/api/v1/bills/${billId}/adjustments/${adjustmentId}`,
    {
      method: 'DELETE',
      token: token ?? undefined,
    },
  )
}

/** `POST /api/v1/bills/{id}/finalize` — locks the bill; no further edits. */
export function finalizeBill(
  billId: string,
  token: string | null,
): Promise<BillResponse> {
  return apiRequest<BillResponse>(`/api/v1/bills/${billId}/finalize`, {
    method: 'POST',
    token: token ?? undefined,
  })
}