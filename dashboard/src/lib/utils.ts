/** Join class names, dropping falsy values (conditional classes). */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}

/**
 * Format a backend timestamp ("YYYY-MM-DD HH:MM:SS", local time) for display.
 * Returns "—" for empty values and the raw string if it can't be parsed.
 */
export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString()
}

/** Format a duration in seconds as a compact "1h 2m 3s" string. */
export function formatDuration(seconds: number | string): string {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const parts: string[] = []
  if (h) parts.push(`${h}h`)
  if (m) parts.push(`${m}m`)
  parts.push(`${s}s`)
  return parts.join(' ')
}
