import type { WizardState } from '../index'
import { Button } from '@/components/ui/Button'
import { Zap, Shield, Car, BarChart3 } from 'lucide-react'

interface Props {
  state: WizardState
  update: (p: Partial<WizardState>) => void
  next: () => void
  back: () => void
  finish: () => void
}

const features = [
  {
    icon: Car,
    title: 'Multiple vehicles',
    desc: 'Manage several Tesla vehicles from one installation.',
  },
  {
    icon: BarChart3,
    title: 'Smart throttling',
    desc: 'Dynamically reduce charging when your home is near its circuit limit.',
  },
  {
    icon: Shield,
    title: 'Energy monitor',
    desc: 'Reads your Shelly EM to track real-time home power consumption.',
  },
]

export function Step1Welcome({ next }: Props) {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <div className="w-16 h-16 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto">
          <Zap size={32} className="text-white" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Welcome to Tesla Smart Charger</h1>
        <p className="text-slate-500 max-w-md mx-auto">
          This wizard will walk you through connecting your Tesla vehicles, configuring your
          home energy monitor, and setting your circuit limits.
        </p>
      </div>

      <div className="grid gap-4">
        {features.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="flex gap-4 p-4 card">
            <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center shrink-0">
              <Icon size={20} className="text-brand-600" />
            </div>
            <div>
              <p className="font-medium text-slate-900">{title}</p>
              <p className="text-sm text-slate-500">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        <p className="font-medium mb-1">Prerequisites</p>
        <ul className="list-disc list-inside space-y-1 text-amber-700">
          <li>A Tesla developer account and registered application</li>
          <li>The <code>tesla-http-proxy</code> container running (see docs)</li>
          <li>Your Shelly EM device on the local network</li>
        </ul>
      </div>

      <Button onClick={next} size="lg" className="w-full">
        Get started
      </Button>
    </div>
  )
}
