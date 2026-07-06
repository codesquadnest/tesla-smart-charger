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
}
