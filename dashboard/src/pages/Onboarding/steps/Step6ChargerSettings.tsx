import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step6ChargerSettings({ state, update, next, back }: Props) {
  const getSettings = (id: number) =>
    state.vehicleSettings[id] ?? {
      chargerMaxAmps: 25,
      chargerMinAmps: 6,
      priority: 1,
    }

  const setField = (id: number, field: string, value: number) => {
    update({
      vehicleSettings: {
        ...state.vehicleSettings,
        [id]: { ...getSettings(id), [field]: value },
      },
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Charger Settings</h2>
        <p className="text-sm text-slate-500 mt-1">
          Set the charging limits for each vehicle. Priority 1 = highest (last to be throttled).
        </p>
      </div>

      <div className="space-y-4">
        {state.selectedTeslaVehicles.map((v, idx) => {
          const s = getSettings(v.id)
          return (
            <div key={v.id} className="card p-5 space-y-4">
              <h3 className="font-semibold text-slate-900">
                {v.display_name || `Vehicle ${idx + 1}`}
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Max amps (A)"
                  type="number"
                  min={1}
                  max={80}
                  value={s.chargerMaxAmps}
                  onChange={(e) => setField(v.id, 'chargerMaxAmps', Number(e.target.value))}
                />
                <Input
                  label="Min amps (A)"
                  type="number"
                  min={1}
                  max={80}
                  value={s.chargerMinAmps}
                  onChange={(e) => setField(v.id, 'chargerMinAmps', Number(e.target.value))}
                />
              </div>
              <Input
                label="Priority (1 = highest)"
                type="number"
                min={1}
                max={10}
                value={s.priority}
                onChange={(e) => setField(v.id, 'priority', Number(e.target.value))}
                hint="In priority mode: lower number = protected from throttling."
              />
            </div>
          )
        })}
      </div>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
