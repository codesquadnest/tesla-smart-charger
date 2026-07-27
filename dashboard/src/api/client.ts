import { getAuthHeader, signOut } from '@/lib/authStore'

const BASE = '/api/v1'

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const auth = getAuthHeader()
  const res = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(auth ? { Authorization: auth } : {}),
      ...options.headers,
    },
    ...options,
  })
  if (!res.ok) {
    // Stored credentials were rejected — drop them so the UI falls back to its
    // locked state instead of retrying with the same bad pair.
    if (res.status === 401) signOut()
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  BASE,
}
