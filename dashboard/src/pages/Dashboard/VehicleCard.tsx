import { useState } from 'react'
import { RefreshCw, Power, Lock, BatteryCharging } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import { Input } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import {
  useRefreshVehicle,
  useWakeVehicle,
  useSetChargeLimit,
  useStartCharge,
  useStopCharge,
} from '@/hooks/useVehicles'
import { cn, formatAge } from '@/lib/utils'
import type { VehicleStatus } from '@/lib/types'

const CHARGE_LIMIT_MIN = 50
const CHARGE_LIMIT_MAX = 100

interface Props {
  vehicle: VehicleStatus
  /** Ticking clock, so the telemetry age counts up between polls. */
  now: number
  /** When the status response that produced `vehicle` landed. */
  dataUpdatedAt: number
  /**
   * Whether command controls are usable — Basic Auth configured on the backend
   * *and* credentials held in this tab. The API fails closed either way; this
   * just stops us offering buttons that are guaranteed to 401/403.
   */
  canCommand: boolean
}

export function VehicleCard({
  vehicle: v,
  now,
  dataUpdatedAt,
  canCommand,
}: Props) {
  const [editingLimit, setEditingLimit] = useState(false)

  const refresh = useRefreshVehicle()
  const wake = useWakeVehicle()
  const startCharge = useStartCharge(v.id)
  const stopCharge = useStopCharge(v.id)

  const chargePct =
    v.chargerActualCurrent != null && v.chargerMaxAmps > 0
      ? Math.max(0, Math.min(100, Math.round((v.chargerActualCurrent / v.chargerMaxAmps) * 100)))
      : null

  // The backend measures age server-side (its cache timestamp is process-local
  // and not comparable to a browser clock); add the time elapsed locally since
  // this response arrived so the label ticks instead of jumping every poll.
  const ageSecs =
    v.telemetryAgeSecs == null
      ? null
      : v.telemetryAgeSecs + (now - dataUpdatedAt) / 1000

  const busy = v.refreshing || refresh.isPending
  const actionError = (refresh.error ?? wake.error ?? startCharge.error ?? stopCharge.error) as Error | null

  // Only offer Wake once we've actually confirmed the car is offline. While
  // `pending` we haven't checked yet, and without a teslaVehicleId the wake
  // call would 400.
  const showWake = !v.pending && v.online === false && Boolean(v.teslaVehicleId)

  // Show start/stop charge buttons when vehicle is online and we have command access
  // Tesla charging_state values: Charging, Supercharging, Starting, Complete, Stopped, Disconnected, NoPower
  const isCharging = ['Charging', 'Supercharging'].includes(v.chargingState ?? '')
    || (v.chargerActualCurrent != null && v.chargerActualCurrent > 0)
  const isStarting = v.chargingState === 'Starting'
  const showChargeControls = canCommand && v.online === true && !v.pending && !isStarting

  return (
    <Card>
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="font-semibold text-slate-900">{v.name || 'Tesla Vehicle'}</p>
          {v.vin && <p className="text-xs text-slate-400">VIN: {v.vin}</p>}
        </div>
        {v.pending ? <Spinner size={16} /> : <OnlineBadge online={v.online} />}
      </div>

      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Charging</span>
          <span className="font-medium text-slate-900">
            {v.pending ? 'Fetching…' : (v.chargingState ?? '—')}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Current</span>
          <span className="font-medium text-slate-900">
            {v.pending
              ? 'Fetching…'
              : v.chargerActualCurrent != null
                ? `${v.chargerActualCurrent} A`
                : '—'}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Battery</span>
          <span className="font-medium text-slate-900">
            {v.pending ? 'Fetching…' : v.batteryLevel != null ? `${v.batteryLevel}%` : '—'}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Charge limit</span>
          <span className="font-medium text-slate-900">
            {v.pending ? 'Fetching…' : v.chargeLimitSoc != null ? `${v.chargeLimitSoc}%` : '—'}
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

      {canCommand && editingLimit && (
        <ChargeLimitForm
          vehicleId={v.id}
          current={v.chargeLimitSoc}
          onClose={() => setEditingLimit(false)}
        />
      )}

      {actionError && (
        <Alert type="error" className="mt-3">
          {actionError.message}
        </Alert>
      )}

      <div className="flex items-center justify-between gap-2 mt-4 pt-3 border-t border-slate-100">
        <span className="text-xs text-slate-400">
          {busy ? 'Refreshing…' : `Updated ${formatAge(ageSecs)}`}
        </span>
        {canCommand ? (
          <div className="flex items-center gap-1">
            {showWake && (
              <Button
                variant="secondary"
                size="sm"
                loading={wake.isPending}
                onClick={() => wake.mutate(v.id)}
              >
                <Power size={14} />
                Wake
              </Button>
            )}
            {showChargeControls && !isCharging && (
              <Button
                variant="primary"
                size="sm"
                loading={startCharge.isPending}
                onClick={() => startCharge.mutate()}
              >
                <BatteryCharging size={14} />
                Start
              </Button>
            )}
            {showChargeControls && isCharging && (
              <Button
                variant="danger"
                size="sm"
                loading={stopCharge.isPending}
                onClick={() => stopCharge.mutate()}
              >
                <Power size={14} />
                Stop
              </Button>
            )}
            {/* Not gated on `busy` — it only toggles a local form, and a
                background refresh every third poll would otherwise keep
                flickering it out of reach. */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEditingLimit((open) => !open)}
            >
              Limit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              title="Refresh vehicle data"
              onClick={() => refresh.mutate(v.id)}
            >
              <RefreshCw size={14} className={cn(busy && 'animate-spin')} />
            </Button>
          </div>
        ) : (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Lock size={12} />
            Controls locked
          </span>
        )}
      </div>
    </Card>
  )
}

function ChargeLimitForm({
  vehicleId,
  current,
  onClose,
}: {
  vehicleId: string
  current: number | null
  onClose: () => void
}) {
  const [percent, setPercent] = useState(current ?? 80)
  const setLimit = useSetChargeLimit(vehicleId)

  const save = async () => {
    await setLimit.mutateAsync(percent)
    onClose()
  }

  return (
    <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
      <Input
        label="Charge limit (%)"
        type="number"
        min={CHARGE_LIMIT_MIN}
        max={CHARGE_LIMIT_MAX}
        step={5}
        value={percent}
        onChange={(e) => setPercent(e.target.valueAsNumber)}
        hint={`Between ${CHARGE_LIMIT_MIN} and ${CHARGE_LIMIT_MAX}`}
      />
      {setLimit.error && (
        <Alert type="error">{(setLimit.error as Error).message}</Alert>
      )}
      <div className="flex gap-2">
        <Button
          size="sm"
          loading={setLimit.isPending}
          disabled={
            Number.isNaN(percent) ||
            percent < CHARGE_LIMIT_MIN ||
            percent > CHARGE_LIMIT_MAX
          }
          onClick={save}
        >
          Set
        </Button>
        <Button variant="secondary" size="sm" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </div>
  )
}

function OnlineBadge({ online }: { online: boolean | null }) {
  if (online === null)
    return <span className="badge-slate">Unknown</span>
  if (online)
    return <span className="badge-green">● Online</span>
  return <span className="badge-red">● Offline</span>
}
