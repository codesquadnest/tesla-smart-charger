import { useStatus } from '@/hooks/useStatus'
import { useNow } from '@/hooks/useNow'
import { useCommandAuth } from '@/hooks/useCommandAuth'
import { Card, StatCard } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { Zap, Thermometer, Activity, BatteryCharging } from 'lucide-react'
import { VehicleCard } from './VehicleCard'
import { CommandAccess } from './CommandAccess'

export default function DashboardPage() {
  const { data: status, isLoading, error, dataUpdatedAt } = useStatus()
  const now = useNow()
  const signedIn = useCommandAuth()
  const canCommand = Boolean(status?.authEnabled) && signedIn

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
        <p className="text-slate-500 text-sm mt-1">
          Live system state — each vehicle card shows when its data was last fetched
        </p>
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
          <div className="space-y-4">
            <CommandAccess authEnabled={status.authEnabled} signedIn={signedIn} />
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {status.vehicles.map((v) => (
                <VehicleCard
                  key={v.id}
                  vehicle={v}
                  now={now}
                  dataUpdatedAt={dataUpdatedAt}
                  canCommand={canCommand}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
