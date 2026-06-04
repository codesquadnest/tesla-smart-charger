import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step9Security({ state, update, next, back }: Props) {
  const valid =
    !state.authEnabled ||
    (state.authUsername.trim().length > 0 && state.authPassword.trim().length >= 8)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Security</h2>
        <p className="text-sm text-slate-500 mt-1">
          Optionally protect the dashboard and API with a username and password.
        </p>
      </div>

      <Alert type="warning">
        This app is designed for local network use. If you expose it to the
        internet, enabling authentication is strongly recommended.
      </Alert>

      <div className="card p-6 space-y-5">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            checked={state.authEnabled}
            onChange={(e) => update({ authEnabled: e.target.checked })}
          />
          <span className="text-sm font-medium text-slate-700">
            Enable HTTP Basic Auth
          </span>
        </label>

        {state.authEnabled && (
          <>
            <Input
              label="Username"
              value={state.authUsername}
              onChange={(e) => update({ authUsername: e.target.value })}
            />
            <Input
              label="Password"
              type="password"
              value={state.authPassword}
              onChange={(e) => update({ authPassword: e.target.value })}
              hint="Minimum 8 characters."
              error={
                state.authPassword.length > 0 && state.authPassword.length < 8
                  ? 'Password must be at least 8 characters.'
                  : undefined
              }
            />
          </>
        )}
      </div>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!valid} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
