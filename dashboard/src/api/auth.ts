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
    client_secret: string
    redirect_uri: string
    proxy_url: string
    region: string
  }) => api.post<AuthStartResponse>('/auth/start', params),

  exchange: (code: string, state: string, issuer?: string) =>
    api.post<AuthCallbackResponse>('/auth/exchange', { code, state, issuer }),

  getResult: (state: string) =>
    api.get<AuthCallbackResponse>(`/auth/result/${state}`),

  listVehicles: (access_token: string, proxy_url: string, region: string) =>
    api.post<{ vehicles: TeslaVehicle[] }>('/auth/vehicles', { access_token, proxy_url, region }),

  setupBasicAuth: (body: AuthSetupBody) =>
    api.post<{ message: string }>('/api/v1/auth/setup', body),

  verify: (username: string, password: string) =>
    api.post<{ valid: boolean }>('/api/v1/auth/verify', { username, password }),
}
