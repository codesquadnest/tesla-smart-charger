import { api } from './client'
import type { TeslaVehicle } from '@/lib/types'

interface AuthStartResponse {
  auth_url: string
  state: string
}

interface AuthCallbackResponse {
  access_token: string
  refresh_token: string
  client_id: string
  proxy_url: string
  region: string
  vehicles: TeslaVehicle[]
}

interface AuthSetupBody {
  enabled: boolean
  username?: string
  password?: string
}

export const authApi = {
  start: (params: {
    client_id: string
    redirect_uri: string
    proxy_url: string
    region: string
  }) => {
    const qs = new URLSearchParams(params as Record<string, string>)
    return api.get<AuthStartResponse>(`/auth/start?${qs}`)
  },

  listVehicles: (access_token: string, proxy_url: string) => {
    const qs = new URLSearchParams({ access_token, proxy_url })
    return api.get<{ vehicles: TeslaVehicle[] }>(`/auth/vehicles?${qs}`)
  },

  setupBasicAuth: (body: AuthSetupBody) =>
    api.post<{ message: string }>('/api/v1/auth/setup', body),

  verify: (username: string, password: string) =>
    api.post<{ valid: boolean }>(`/api/v1/auth/verify?username=${encodeURIComponent(username)}`, { password }),
}
