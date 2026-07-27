import { useEffect, useState } from 'react'

/**
 * Ticking wall-clock, so elapsed-time labels count up between data fetches.
 *
 * Call this once high in the tree and pass the value down — one timer per
 * component would mean N timers and N independent re-render cascades.
 */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])

  return now
}
