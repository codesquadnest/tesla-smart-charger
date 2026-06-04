import { useStatus } from '@/hooks/useStatus'
import { Card, StatCard } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { Zap, Thermometer, Activity, BatteryCharging } from 'lucide-react'
import type { VehicleStatus } from '@/lib/types'
// Badge styles are applied directly via CSS utility classes (badge-green, badge-red, etc.)

export default function DashboardPage() {
  const { data: status, isLoading, error } = useStatus()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size={32} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <Alert type="error" title="Could not load status">
          {(error as Error).message}
        </Alert>
      </div>
    )
  }

  if (!status) return null

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Live system state — refreshes every 10 seconds</p>
      </div>

      {/* Overload banner */}
      {status.overloadActive && (
        <Alert type="warning" title="Overload session active">
          An overload is currently being handled. Charging amps are being throttled.
        </Alert>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Home consumption"
          value={
            status.currentConsumptionAmps != null
              ? `${status.currentConsumptionAmps.toFixed(1)} A`
              : '—'
          }
          sub={`Max: ${status.homeMaxAmps} A`}
          icon={<Activity size={18} />}
          accent={
            status.currentConsumptionAmps != null &&
            status.currentConsumptionAmps > status.homeMaxAmps
              ? 'red'
              : 'default'
          }
        />
        <StatCard
          label="Vehicles"
          value={status.vehicles.length}
          sub={`${status.vehicles.filter((v) => v.online).length} online`}
          icon={<Zap size={18} />}
        />
        <StatCard
          label="Monitor"
          value={status.monitorActive ? 'Active' : 'Inactive'}
          icon={<Thermometer size={18} />}
          accent={status.monitorActive ? 'green' : 'default'}
        />
        <StatCard
          label="Region"
          value={status.region.toUpperCase()}
          sub={`${status.voltage}V grid`}
          icon={<BatteryCharging size={18} />}
        />
      </div>

      {/* Vehicle cards */}
      <div>
        <h2 className="text-base font-semibold text-slate-900 mb-4">Vehicles</h2>
        {status.vehicles.length === 0 ? (
          <Card className="text-center py-12 text-slate-500">
            No vehicles configured yet.
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {status.vehicles.map((v) => (
              <VehicleCard key={v.id} vehicle={v} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function VehicleCard({ vehicle: v }: { vehicle: VehicleStatus }) {
  const chargePct =
    v.chargerActualCurrent != null
      ? Math.round((v.chargerActualCurrent / v.chargerMaxAmps) * 100)
      : null

  return (
    <Card>
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="font-semibold text-slate-900">{v.name || 'Tesla Vehicle'}</p>
          {v.vin && <p className="text-xs text-slate-400">VIN: {v.vin}</p>}
        </div>
        <OnlineBadge online={v.online} />
      </div>

      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Charging</span>
          <span className="font-medium text-slate-900">
            {v.chargingState ?? '—'}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Current</span>
          <span className="font-medium text-slate-900">
            {v.chargerActualCurrent != null
              ? `${v.chargerActualCurrent} A`
              : '—'}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Battery</span>
          <span className="font-medium text-slate-900">
            {v.batteryLevel != null ? `${v.batteryLevel}%` : '—'}
          </span>
        </div>

        {chargePct != null && (
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Charge rate</span>
              <span>
                {v.chargerActualCurrent}A / {v.chargerMaxAmps}A
              </span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all"
                style={{ width: `${chargePct}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}

function OnlineBadge({ online }: { online: boolean | null }) {
  if (online === null)
    return <span className="badge-slate">Unknown</span>
  if (online)
    return <span className="badge-green">● Online</span>
  return <span className="badge-red">● Offline</span>
}
