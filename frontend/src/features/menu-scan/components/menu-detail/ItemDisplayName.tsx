import type { BillItem } from '@/features/menu-scan/types'

export interface ItemDisplayNameProps {
  item: BillItem
  /** Tailwind classes applied to the parenthesised original-name span. */
  originalClassName?: string
}

/** Shows the translated name with the original name in parentheses when they
 * differ; otherwise just the original name. */
export function ItemDisplayName({
  item,
  originalClassName = 'text-ink-variant/40',
}: ItemDisplayNameProps) {
  if (item.translated_name && item.translated_name !== item.original_name) {
    return (
      <>
        {item.translated_name}
        <span className={`ml-1 font-medium ${originalClassName}`}>
          ({item.original_name})
        </span>
      </>
    )
  }
  return item.original_name
}
