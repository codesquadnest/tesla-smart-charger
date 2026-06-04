import { api } from './client'
import type { SystemConfig } from '@/lib/types'

export const configApi = {
  get: () => api.get<SystemConfig>('/api/v1/config'),
  update: (body: Partial<SystemConfig>) => api.post<SystemConfig>('/api/v1/config', body),
}
