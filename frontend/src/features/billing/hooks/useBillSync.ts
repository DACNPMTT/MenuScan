import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/shared/lib/api'
import {
  addAdjustment as apiAddAdjustment,
  createBill,
  finalizeBill,
  removeAdjustment as apiRemoveAdjustment,
  replaceBillItems,
  updateAdjustment as apiUpdateAdjustment,
} from '@/features/billing/api'
import type { AdjustmentInput, BillResponse } from '@/features/billing/types'

const SYNC_DEBOUNCE_MS = 600

interface UseBillSyncResult {
  bill: BillResponse | null
  syncing: boolean
  syncError: string | null
  isFinalized: boolean
  retrySync: () => void
  finalize: () => Promise<void>
  addAdjustment: (payload: AdjustmentInput) => Promise<void>
  updateAdjustment: (adjustmentId: string, payload: AdjustmentInput) => Promise<void>
  removeAdjustment: (adjustmentId: string) => Promise<void>
}

/**
 * Owns the DRAFT bill lifecycle for `BillingWorkspace`: lazily creates the
 * bill on first selection, debounces item-quantity syncs, and exposes
 * adjustment/finalize mutations. Extracted out of the component so the
 * component tree only deals with rendering (matches the split used by
 * `features/menu-scan/hooks/useCamera.ts` and `features/auth/hooks/useMagicLink.ts`).
 */
export function useBillSync(
  menuId: string,
  quantities: Record<string, number>,
  accessToken: string | null,
): UseBillSyncResult {
  const [bill, setBill] = useState<BillResponse | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)

  const billIdRef = useRef<string | null>(null)
  const debounceRef = useRef<number | undefined>(undefined)
  // Guards against a stale response overwriting a newer one when two syncs
  // are in flight back to back.
  const requestSeq = useRef(0)

  const isFinalized = bill?.status === 'FINALIZED'

  const syncItems = useCallback(
    async (nextQuantities: Record<string, number>) => {
      if (!accessToken) return
      const seq = ++requestSeq.current
      setSyncing(true)
      setSyncError(null)
      try {
        let id = billIdRef.current
        if (!id) {
          if (Object.keys(nextQuantities).length === 0) {
            setSyncing(false)
            return
          }
          const created = await createBill(menuId, accessToken)
          id = created.id
          billIdRef.current = id
        }
        const payload = Object.entries(nextQuantities).map(([foodItemId, quantity]) => ({
          food_item_id: foodItemId,
          quantity,
        }))
        const updated = await replaceBillItems(id, payload, accessToken)
        if (seq === requestSeq.current) setBill(updated)
      } catch (err) {
        if (seq === requestSeq.current) {
          setSyncError(err instanceof ApiError ? err.message : 'Không thể cập nhật hóa đơn.')
        }
      } finally {
        if (seq === requestSeq.current) setSyncing(false)
      }
    },
    [accessToken, menuId],
  )

  useEffect(() => {
    if (!accessToken || isFinalized) return
    window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => {
      void syncItems(quantities)
    }, SYNC_DEBOUNCE_MS)
    return () => window.clearTimeout(debounceRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quantities, accessToken, isFinalized])

  const retrySync = useCallback(() => {
    void syncItems(quantities)
  }, [syncItems, quantities])

  const finalize = useCallback(async () => {
    if (!bill || isFinalized || syncing) return
    setSyncing(true)
    setSyncError(null)
    try {
      const finalized = await finalizeBill(bill.id, accessToken)
      setBill(finalized)
    } catch (err) {
      setSyncError(err instanceof ApiError ? err.message : 'Không thể chốt hóa đơn.')
    } finally {
      setSyncing(false)
    }
  }, [bill, isFinalized, syncing, accessToken])

  const addAdjustment = useCallback(
    async (payload: AdjustmentInput) => {
      if (!billIdRef.current) return
      setSyncing(true)
      setSyncError(null)
      try {
        const updated = await apiAddAdjustment(billIdRef.current, payload, accessToken)
        setBill(updated)
      } catch (err) {
        setSyncError(err instanceof ApiError ? err.message : 'Không thể thêm khoản điều chỉnh.')
        throw err
      } finally {
        setSyncing(false)
      }
    },
    [accessToken],
  )

  const updateAdjustment = useCallback(
    async (adjustmentId: string, payload: AdjustmentInput) => {
      if (!billIdRef.current) return
      setSyncing(true)
      setSyncError(null)
      try {
        const updated = await apiUpdateAdjustment(
          billIdRef.current,
          adjustmentId,
          payload,
          accessToken,
        )
        setBill(updated)
      } catch (err) {
        setSyncError(err instanceof ApiError ? err.message : 'Không thể cập nhật khoản điều chỉnh.')
        throw err
      } finally {
        setSyncing(false)
      }
    },
    [accessToken],
  )

  const removeAdjustment = useCallback(
    async (adjustmentId: string) => {
      if (!billIdRef.current) return
      setSyncing(true)
      setSyncError(null)
      try {
        const updated = await apiRemoveAdjustment(billIdRef.current, adjustmentId, accessToken)
        setBill(updated)
      } catch (err) {
        setSyncError(err instanceof ApiError ? err.message : 'Không thể xóa khoản điều chỉnh.')
      } finally {
        setSyncing(false)
      }
    },
    [accessToken],
  )

  return {
    bill,
    syncing,
    syncError,
    isFinalized,
    retrySync,
    finalize,
    addAdjustment,
    updateAdjustment,
    removeAdjustment,
  }
}