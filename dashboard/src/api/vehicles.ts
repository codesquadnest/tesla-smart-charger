import { api } from './client'
import type { Vehicle, TeslaVehicle } from '@/lib/types'

export const vehiclesApi = {
  list: () => api.get<Vehicle[]>('/api/v1/vehicles'),
  get: (id: string) => api.get<Vehicle>(`/api/v1/vehicles/${id}`),
  add: (body: Partial<Vehicle>) => api.post<Vehicle>('/api/v1/vehicles', body),
  update: (id: string, body: Partial<Vehicle>) =>
    api.patch<Vehicle>(`/api/v1/vehicles/${id}`, body),
  remove: (id: string) => api.del<{ message: string }>(`/api/v1/vehicles/${id}`),
  listTeslaVehicles: (id: string) =>
    api.get<{ vehicles: TeslaVehicle[] }>(`/api/v1/vehicles/${id}/tesla-vehicles`),

  wake: (id: string) =>
    api.post<{ message: string; state: string | null }>(
      `/api/v1/vehicles/${id}/wake`,
      {},
    ),
  setChargeLimit: (id: string, percent: number) =>
    api.post<{ message: string; percent: number }>(
      `/api/v1/vehicles/${id}/charge-limit`,
      { percent },
    ),
  refresh: (id: string) =>
    api.post<{ message: string; refreshing: boolean }>(
      `/api/v1/vehicles/${id}/refresh`,
      {},
    ),
}
