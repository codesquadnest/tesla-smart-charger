import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import { ExternalLink } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step3TeslaApp({ state, update, next, back }: Props) {
  const canContinue = state.clientId.trim().length > 0 && state.proxyUrl.trim().length > 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Tesla Application</h2>
        <p className="text-sm text-slate-500 mt-1">
          Enter your Tesla developer app credentials and the local proxy URL.
        </p>
      </div>

      <Alert type="info" title="Need a Tesla developer app?">
        Visit{' '}
        <a
          href="https://developer.tesla.com"
          target="_blank"
          rel="noopener noreferrer"
          className="underline font-medium inline-flex items-center gap-1"
        >
          developer.tesla.com <ExternalLink size={12} />
        </a>{' '}
        to register your application and obtain a Client ID. Set the redirect URI to:
        <code className="block mt-1 bg-white border border-blue-200 rounded px-2 py-1 text-xs font-mono break-all">
          {state.redirectUri}
        </code>
      </Alert>

      <div className="card p-6 space-y-5">
        <Input
          label="Tesla Client ID"
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          value={state.clientId}
          onChange={(e) => update({ clientId: e.target.value })}
        />

        <Input
          label="tesla-http-proxy URL"
          placeholder="http://localhost:4443"
          value={state.proxyUrl}
          onChange={(e) => update({ proxyUrl: e.target.value })}
          hint="The URL of your running tesla-http-proxy container."
        />

        <Input
          label="OAuth redirect URI"
          value={state.redirectUri}
          onChange={(e) => update({ redirectUri: e.target.value })}
          hint="Must match the redirect URI registered in your Tesla developer app."
        />
      </div>

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!canContinue} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
