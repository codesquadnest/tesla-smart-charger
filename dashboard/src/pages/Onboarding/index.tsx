import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'

// Steps
import { Step1Welcome } from './steps/Step1Welcome'
import { Step2RegionVoltage } from './steps/Step2RegionVoltage'
import { Step3TeslaApp } from './steps/Step3TeslaApp'
import { Step4TeslaAuth } from './steps/Step4TeslaAuth'
import { Step5SelectVehicles } from './steps/Step5SelectVehicles'
import { Step6ChargerSettings } from './steps/Step6ChargerSettings'
import { Step7EnergyMonitor } from './steps/Step7EnergyMonitor'
import { Step8CircuitStrategy } from './steps/Step8CircuitStrategy'
import { Step9Security } from './steps/Step9Security'
import { Step10Done } from './steps/Step10Done'

export interface WizardState {
  // Step 2
  region: string
  voltage: number
  // Step 3
  clientId: string
  proxyUrl: string
  redirectUri: string
  // Step 4 (OAuth result)
  accessToken: string
  refreshToken: string
  // Step 5 (selected vehicles from Tesla)
  selectedTeslaVehicles: Array<{
    id: number
    vin: string
    display_name: string
  }>
  // Step 6 (per-vehicle charger settings)
  vehicleSettings: Record<
    number,
    { chargerMaxAmps: number; chargerMinAmps: number; priority: number }
  >
  // Step 7
  energyMonitorIp: string
  energyMonitorType: string
  // Step 8
  homeMaxAmps: number
  sleepTimeSecs: number
  downStepPercentage: number
  overloadStrategy: string
  // Step 9
  authEnabled: boolean
  authUsername: string
  authPassword: string
}

const TOTAL_STEPS = 10

const STEP_LABELS = [
  'Welcome',
  'Region & Voltage',
  'Tesla App',
  'Authorize',
  'Select Vehicles',
  'Charger Settings',
  'Energy Monitor',
  'Circuit & Strategy',
  'Security',
  'Done',
]

export default function OnboardingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState(1)
  const [state, setState] = useState<WizardState>({
    region: 'eu',
    voltage: 230,
    clientId: '',
    proxyUrl: 'http://localhost:4443',
    redirectUri: `${window.location.origin}/auth/callback`,
    accessToken: '',
    refreshToken: '',
    selectedTeslaVehicles: [],
    vehicleSettings: {},
    energyMonitorIp: '',
    energyMonitorType: 'shelly_em',
    homeMaxAmps: 30,
    sleepTimeSecs: 30,
    downStepPercentage: 0.5,
    overloadStrategy: 'proportional',
    authEnabled: false,
    authUsername: '',
    authPassword: '',
  })

  const update = (patch: Partial<WizardState>) =>
    setState((prev) => ({ ...prev, ...patch }))

  const next = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS))
  const back = () => setStep((s) => Math.max(s - 1, 1))

  const finish = () => {
    queryClient.invalidateQueries({ queryKey: ['status'] })
    navigate('/')
  }

  const stepProps = { state, update, next, back, finish }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
          <Zap size={16} className="text-white" />
        </div>
        <span className="font-semibold text-slate-900">Tesla Smart Charger — Setup</span>
      </header>

      <div className="flex-1 flex">
        {/* Step indicator sidebar */}
        <div className="w-52 shrink-0 bg-white border-r border-slate-200 py-8 px-4 hidden md:block">
          <ol className="space-y-2">
            {STEP_LABELS.map((label, i) => {
              const num = i + 1
              const done = num < step
              const active = num === step
              return (
                <li
                  key={num}
                  className="flex items-center gap-3 text-sm"
                >
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 ${
                      done
                        ? 'bg-green-500 text-white'
                        : active
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-200 text-slate-500'
                    }`}
                  >
                    {done ? '✓' : num}
                  </span>
                  <span
                    className={
                      active
                        ? 'font-medium text-slate-900'
                        : done
                        ? 'text-slate-500'
                        : 'text-slate-400'
                    }
                  >
                    {label}
                  </span>
                </li>
              )
            })}
          </ol>
        </div>

        {/* Step content */}
        <div className="flex-1 flex items-start justify-center py-10 px-4">
          <div className="w-full max-w-xl">
            {/* Mobile step indicator */}
            <p className="text-xs text-slate-500 mb-4 md:hidden">
              Step {step} of {TOTAL_STEPS} — {STEP_LABELS[step - 1]}
            </p>

            {step === 1 && <Step1Welcome {...stepProps} />}
            {step === 2 && <Step2RegionVoltage {...stepProps} />}
            {step === 3 && <Step3TeslaApp {...stepProps} />}
            {step === 4 && <Step4TeslaAuth {...stepProps} />}
            {step === 5 && <Step5SelectVehicles {...stepProps} />}
            {step === 6 && <Step6ChargerSettings {...stepProps} />}
            {step === 7 && <Step7EnergyMonitor {...stepProps} />}
            {step === 8 && <Step8CircuitStrategy {...stepProps} />}
            {step === 9 && <Step9Security {...stepProps} />}
            {step === 10 && <Step10Done {...stepProps} />}
          </div>
        </div>
      </div>
    </div>
  )
}
