// Shared API types — mirror the Pydantic models in tesla_smart_charger/models.py
// and the JSON returned by the FastAPI routes.

export type Region = 'eu' | 'na' | 'ap'
export type OverloadStrategyType = 'proportional' | 'priority'

/** HTTP Basic Auth config. `passwordHash` is redacted by the backend. */
export interface AuthConfig {
  enabled: boolean
  username: string
}

/** System-wide configuration — GET/POST /api/v1/config. */
export interface SystemConfig {
  homeMaxAmps: number
  voltage: number
  region: Region
  energyMonitorIp: string
  energyMonitorType: string
  sleepTimeSecs: number
  downStepPercentage: number
  upStepPercentage: number
  overloadStrategy: OverloadStrategyType
  maxSessionDuration: number
  hostIp: string
  apiPort: number
  corsOrigins: string[]
  auth: AuthConfig
  configured: boolean
}

/** Live status for a single vehicle (config merged with telemetry). */
export interface VehicleStatus {
  id: string
  name: string
  vin: string
  teslaVehicleId: string
  teslaHttpProxy: string
  chargerMaxAmps: number
  chargerMinAmps: number
  priority: number
  enabled: boolean
  // Live fields — null when the vehicle is offline / unreachable
  online: boolean | null
  chargingState: string | null
  chargerActualCurrent: number | null
  batteryLevel: number | null
}

/** Overall system status — GET /api/v1/status. */
export interface SystemStatus {
  configured: boolean
  monitorActive: boolean
  overloadActive: boolean
  currentConsumptionAmps: number | null
  homeMaxAmps: number
  region: string
  voltage: number
  vehicles: VehicleStatus[]
}

/** A managed vehicle — /api/v1/vehicles (tokens redacted in responses). */
export interface Vehicle {
  id: string
  name: string
  vin: string
  teslaVehicleId: string
  teslaAccessToken: string
  teslaRefreshToken: string
  teslaHttpProxy: string
  teslaClientId: string
  region: string
  chargerMaxAmps: number
  chargerMinAmps: number
  priority: number
  enabled: boolean
}

/** A vehicle as returned by the Tesla Fleet API (via the proxy). */
export interface TeslaVehicle {
  id: number
  vehicle_id?: number
  vin: string
  display_name: string
  state: string
}

/** A persisted overload event — GET /api/v1/history. */
export interface OverloadEvent {
  id: number
  start: string
  end: string
  duration: number | string
  vehicle_id: string
}
