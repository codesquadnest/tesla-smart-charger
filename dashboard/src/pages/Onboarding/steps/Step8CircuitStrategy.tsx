import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
}

const strategyOptions = [
  {
    value: 'proportional',
    label: 'Proportional — reduce all vehicles equally',
  },
  {
    value: 'priority',
    label: 'Priority — reduce lowest-priority vehicle first',
  },
]

export function Step8CircuitStrategy({ state, update, next, back }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Circuit &amp; Strategy</h2>
        <p className="text-sm text-slate-500 mt-1">
          Configure your home circuit limits and overload response behaviour.
        </p>
      </div>

      <div className="card p-6 space-y-5">
        <Input
          label="Home max amps (A)"
          info="Your main breaker or circuit limit. The app will not let total consumption exceed this."
          type="number"
          min={1}
          max={400}
          value={state.homeMaxAmps}
          onChange={(e) => update({ homeMaxAmps: Number(e.target.value) })}
          hint="Your home circuit breaker limit. The app will not let total consumption exceed this."
        />

        <Select
          label="Overload strategy"
          info="How to distribute load reduction across vehicles when overload is detected."
          value={state.overloadStrategy}
          onChange={(e) => update({ overloadStrategy: e.target.value })}
          options={strategyOptions}
        />

        <Input
          label="Stabilisation sleep time (seconds)"
          info="Seconds between adjustment steps during an overload event. Lower values react faster but may cause more API calls."
          type="number"
          min={5}
          max={300}
          value={state.sleepTimeSecs}
          onChange={(e) => update({ sleepTimeSecs: Number(e.target.value) })}
          hint="How long to wait between adjustment steps during an overload event."
        />

        <Input
          label="Initial downstep multiplier"
          info="First response when overload is detected. Current charge amps are multiplied by this factor (e.g. 0.5 = halve)."
          type="number"
          min={0.1}
          max={1.0}
          step={0.05}
          value={state.downStepPercentage}
          onChange={(e) => update({ downStepPercentage: Number(e.target.value) })}
          hint="First response: multiply current charge amps by this factor (e.g. 0.5 = halve)."
        />

        <Input
          label="Max session duration (seconds)"
          info="Maximum time a supervised overload session can run before ending. Prevents the car from staying stuck at a reduced limit if overload persists."
          type="number"
          min={60}
          max={3600}
          step={30}
          value={state.maxSessionDuration}
          onChange={(e) => update({ maxSessionDuration: Number(e.target.value) })}
          hint="Maximum time a supervised overload session can run before automatically ending (default 600 = 10 min)."
        />
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
