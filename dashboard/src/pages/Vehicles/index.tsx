import { useState } from 'react'
import { useVehicles, useAddVehicle, useUpdateVehicle, useRemoveVehicle } from '@/hooks/useVehicles'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { Plus, Trash2, Edit2, X, Save, Car } from 'lucide-react'
import type { Vehicle } from '@/lib/types'

export default function VehiclesPage() {
  const { data: vehicles = [], isLoading, error } = useVehicles()
  const removeVehicle = useRemoveVehicle()
  const [editing, setEditing] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size={32} />
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Vehicles</h1>
          <p className="text-slate-500 text-sm mt-1">
            Manage your Tesla vehicles and charger settings.
          </p>
        </div>
        <Button onClick={() => setShowAdd(true)} variant="primary">
          <Plus size={16} />
          Add vehicle
        </Button>
      </div>

      {error && (
        <Alert type="error">{(error as Error).message}</Alert>
      )}

      {showAdd && (
        <AddVehicleForm onClose={() => setShowAdd(false)} />
      )}

      {vehicles.length === 0 && !showAdd ? (
        <Card className="text-center py-16">
          <Car size={40} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">No vehicles configured yet.</p>
          <Button onClick={() => setShowAdd(true)} className="mt-4">
            Add your first vehicle
          </Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {vehicles.map((v) =>
            editing === v.id ? (
              <EditVehicleForm
                key={v.id}
                vehicle={v}
                onClose={() => setEditing(null)}
              />
            ) : (
              <VehicleRow
                key={v.id}
                vehicle={v}
                onEdit={() => setEditing(v.id)}
                onRemove={() => removeVehicle.mutate(v.id)}
              />
            )
          )}
        </div>
      )}
    </div>
  )
}

function VehicleRow({
  vehicle: v,
  onEdit,
  onRemove,
}: {
  vehicle: Vehicle
  onEdit: () => void
  onRemove: () => void
}) {
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <Card className="flex items-center gap-4">
      <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center shrink-0">
        <Car size={20} className="text-brand-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-slate-900">{v.name || 'Unnamed Vehicle'}</p>
        <p className="text-xs text-slate-500">
          ID: {v.teslaVehicleId} · VIN: {v.vin || '—'} · Priority: {v.priority}
        </p>
        <p className="text-xs text-slate-400">
          Charger: {v.chargerMinAmps}A–{v.chargerMaxAmps}A ·{' '}
          {v.enabled ? (
            <span className="text-green-600">Enabled</span>
          ) : (
            <span className="text-slate-400">Disabled</span>
          )}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button variant="ghost" size="sm" onClick={onEdit}>
          <Edit2 size={14} />
        </Button>
        {confirmDelete ? (
          <>
            <Button variant="danger" size="sm" onClick={onRemove}>
              Confirm
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </>
        ) : (
          <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(true)}>
            <Trash2 size={14} className="text-red-500" />
          </Button>
        )}
      </div>
    </Card>
  )
}

function EditVehicleForm({
  vehicle,
  onClose,
}: {
  vehicle: Vehicle
  onClose: () => void
}) {
  const update = useUpdateVehicle(vehicle.id)
  const [form, setForm] = useState({
    name: vehicle.name,
    chargerMaxAmps: vehicle.chargerMaxAmps,
    chargerMinAmps: vehicle.chargerMinAmps,
    priority: vehicle.priority,
    enabled: vehicle.enabled,
  })

  const save = async () => {
    await update.mutateAsync(form)
    onClose()
  }

  return (
    <Card className="border-brand-200">
      <div className="flex items-center justify-between mb-4">
        <p className="font-semibold text-slate-900">Edit vehicle</p>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X size={16} />
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Name"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
        />
        <Input
          label="Priority"
          type="number"
          min={1}
          value={form.priority}
          onChange={(e) => setForm((f) => ({ ...f, priority: Number(e.target.value) }))}
        />
        <Input
          label="Max amps (A)"
          type="number"
          min={1}
          value={form.chargerMaxAmps}
          onChange={(e) => setForm((f) => ({ ...f, chargerMaxAmps: Number(e.target.value) }))}
        />
        <Input
          label="Min amps (A)"
          type="number"
          min={1}
          value={form.chargerMinAmps}
          onChange={(e) => setForm((f) => ({ ...f, chargerMinAmps: Number(e.target.value) }))}
        />
      </div>
      <label className="flex items-center gap-2 mt-4 text-sm cursor-pointer">
        <input
          type="checkbox"
          checked={form.enabled}
          onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
          className="rounded border-slate-300"
        />
        <span>Enabled</span>
      </label>
      <div className="flex gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={save} loading={update.isPending}>
          <Save size={14} />
          Save changes
        </Button>
      </div>
      {update.error && (
        <Alert type="error" className="mt-3">
          {(update.error as Error).message}
        </Alert>
      )}
    </Card>
  )
}

function AddVehicleForm({ onClose }: { onClose: () => void }) {
  const add = useAddVehicle()
  const [form, setForm] = useState({
    name: '',
    vin: '',
    teslaVehicleId: '',
    teslaAccessToken: '',
    teslaRefreshToken: '',
    teslaHttpProxy: 'http://localhost:4443',
    teslaClientId: '',
    chargerMaxAmps: 25,
    chargerMinAmps: 6,
    priority: 1,
  })

  const save = async () => {
    await add.mutateAsync(form)
    onClose()
  }

  return (
    <Card className="border-brand-200 bg-brand-50/30">
      <div className="flex items-center justify-between mb-4">
        <p className="font-semibold text-slate-900">Add new vehicle</p>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X size={16} />
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Display name"
          placeholder="Model 3"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
        />
        <Input
          label="VIN (optional)"
          value={form.vin}
          onChange={(e) => setForm((f) => ({ ...f, vin: e.target.value }))}
        />
        <Input
          label="Tesla Vehicle ID"
          placeholder="123456789"
          value={form.teslaVehicleId}
          onChange={(e) => setForm((f) => ({ ...f, teslaVehicleId: e.target.value }))}
        />
        <Input
          label="Tesla Client ID"
          value={form.teslaClientId}
          onChange={(e) => setForm((f) => ({ ...f, teslaClientId: e.target.value }))}
        />
        <div className="col-span-2">
          <Input
            label="Proxy URL"
            value={form.teslaHttpProxy}
            onChange={(e) => setForm((f) => ({ ...f, teslaHttpProxy: e.target.value }))}
          />
        </div>
        <div className="col-span-2">
          <Input
            label="Access token"
            type="password"
            value={form.teslaAccessToken}
            onChange={(e) => setForm((f) => ({ ...f, teslaAccessToken: e.target.value }))}
          />
        </div>
        <div className="col-span-2">
          <Input
            label="Refresh token"
            type="password"
            value={form.teslaRefreshToken}
            onChange={(e) => setForm((f) => ({ ...f, teslaRefreshToken: e.target.value }))}
          />
        </div>
        <Input
          label="Max amps"
          type="number"
          value={form.chargerMaxAmps}
          onChange={(e) => setForm((f) => ({ ...f, chargerMaxAmps: Number(e.target.value) }))}
        />
        <Input
          label="Min amps"
          type="number"
          value={form.chargerMinAmps}
          onChange={(e) => setForm((f) => ({ ...f, chargerMinAmps: Number(e.target.value) }))}
        />
      </div>
      <div className="flex gap-3 mt-4">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={save} loading={add.isPending}>
          <Plus size={14} />
          Add vehicle
        </Button>
      </div>
      {add.error && (
        <Alert type="error" className="mt-3">
          {(add.error as Error).message}
        </Alert>
      )}
    </Card>
  )
}
