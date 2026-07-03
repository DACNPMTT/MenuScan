import { useEffect, useState } from 'react'

/** Returns a copy of `value` that only updates after it has been stable for
 * `delayMs`. Used to coalesce rapid input (e.g. a search box) so we don't fire
 * a request per keystroke. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(id)
  }, [value, delayMs])
  return debounced
}
