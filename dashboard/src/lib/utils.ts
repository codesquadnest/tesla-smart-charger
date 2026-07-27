/** Join class names, dropping falsy values (conditional classes). */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}

/**
 * Resolve a numeric <input>'s value, keeping the previous value when the field
 * is empty/invalid. Prevents clearing an input from silently writing 0.
 */
export function toNum(valueAsNumber: number, prev: number): number {
  return Number.isNaN(valueAsNumber) ? prev : valueAsNumber
}

/**
 * Validate that a string is a usable host for a local fetch — an IPv4 address
 * or a hostname, with no scheme, port, path, or credentials. Used to sanitise
 * the energy-monitor address before probing it.
 */
export function isValidHost(value: string): boolean {
  const host = value.trim()
  if (!host || /[/\\@?#\s]/.test(host) || host.includes(':')) return false
  const ipv4 =
    /^(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)$/
  const hostname = /^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})*$/
  return ipv4.test(host) || hostname.test(host)
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

/** Format an elapsed age in seconds as a compact "just now" / "42s ago" label. */
export function formatAge(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return 'never'
  const total = Math.max(0, Math.round(seconds))
  if (total < 5) return 'just now'
  if (total < 60) return `${total}s ago`
  if (total < 3600) return `${Math.floor(total / 60)}m ago`
  return `${Math.floor(total / 3600)}h ago`
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
