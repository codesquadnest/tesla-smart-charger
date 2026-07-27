/**
 * Basic Auth credentials for the vehicle command endpoints.
 *
 * Held in sessionStorage rather than localStorage so they die with the tab.
 * Only the command routes require them; everything else stays open, so this
 * is an "unlock the controls" credential, not a dashboard-wide login.
 */

const STORAGE_KEY = 'tsc_command_auth'

const listeners = new Set<() => void>()

function read(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    // sessionStorage unavailable (private mode, embedded webview) — treat as
    // signed out rather than breaking the page.
    return null
  }
}

function emit() {
  listeners.forEach((l) => l())
}

/** The `Basic <base64>` header value, or null when signed out. */
export function getAuthHeader(): string | null {
  const encoded = read()
  return encoded ? `Basic ${encoded}` : null
}

/** btoa is Latin1-only; this widens it to arbitrary UTF-8 credentials. */
function toBase64(value: string): string {
  const bytes = new TextEncoder().encode(value)
  const binary = Array.from(bytes, (b) => String.fromCharCode(b)).join('')
  return btoa(binary)
}

export function signIn(username: string, password: string) {
  try {
    sessionStorage.setItem(STORAGE_KEY, toBase64(`${username}:${password}`))
  } catch {
    /* storage unavailable — the sign-in simply won't persist */
  }
  emit()
}

export function signOut() {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* nothing to clear */
  }
  emit()
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getSnapshot(): boolean {
  return read() !== null
}
