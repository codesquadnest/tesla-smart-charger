import { useState } from 'react'
import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'
import { authApi } from '@/api/auth'
import { ExternalLink, CheckCircle } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

export function Step4TeslaAuth({ state, update, next, back }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const authorized = !!state.accessToken

  const handleAuthorize = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await authApi.start({
        client_id: state.clientId,
        redirect_uri: state.redirectUri,
        proxy_url: state.proxyUrl,
        region: state.region,
      })

      // Open Tesla auth in a popup window
      const popup = window.open(
        res.auth_url,
        'tesla-auth',
        'width=600,height=700,scrollbars=yes'
      )

      // Listen for the callback result
      const handler = (event: MessageEvent) => {
        if (event.data?.type === 'tesla-auth-callback') {
          window.removeEventListener('message', handler)
          const { access_token, refresh_token } = event.data
          if (access_token && refresh_token) {
            update({ accessToken: access_token, refreshToken: refresh_token })
          } else {
            setError('Authorization failed — no tokens received.')
          }
          popup?.close()
        }
      }
      window.addEventListener('message', handler)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start authorization.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Authorize with Tesla</h2>
        <p className="text-sm text-slate-500 mt-1">
          Connect your Tesla account so the app can read vehicle data and send
          charging commands.
        </p>
      </div>

      {authorized ? (
        <div className="card p-6 flex items-center gap-3">
          <CheckCircle size={24} className="text-green-500 shrink-0" />
          <div>
            <p className="font-medium text-slate-900">Authorization successful!</p>
            <p className="text-sm text-slate-500">Tokens received and stored in memory.</p>
          </div>
        </div>
      ) : (
        <div className="card p-6 space-y-4">
          <p className="text-sm text-slate-600">
            Clicking the button below will open Tesla&apos;s sign-in page in a popup.
            After you approve access, you&apos;ll be redirected back here automatically.
          </p>

          {error && <Alert type="error">{error}</Alert>}

          <Button
            onClick={handleAuthorize}
            loading={loading}
            size="lg"
            className="w-full"
          >
            <ExternalLink size={16} />
            Connect with Tesla
          </Button>
        </div>
      )}

      <div className="flex gap-3">
        <Button variant="secondary" onClick={back}>
          Back
        </Button>
        <Button onClick={next} disabled={!authorized} className="flex-1">
          Continue
        </Button>
      </div>
    </div>
  )
}
