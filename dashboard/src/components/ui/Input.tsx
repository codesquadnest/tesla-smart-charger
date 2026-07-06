import { cn } from '@/lib/utils'
import type { InputHTMLAttributes, SelectHTMLAttributes } from 'react'
import { InfoTooltip } from './InfoTooltip'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  info?: string
}

export function Input({ label, error, hint, info, className, id, ...props }: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="label">
          {info ? <InfoTooltip text={info}>{label}</InfoTooltip> : label}
        </label>
      )}
      <input
        id={inputId}
        className={cn(
          'input',
          error && 'border-red-400 focus:ring-red-400',
          className
        )}
        {...props}
      />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  info?: string
  options: { value: string; label: string }[]
}

export function Select({ label, error, info, options, className, id, ...props }: SelectProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="label">
          {info ? <InfoTooltip text={info}>{label}</InfoTooltip> : label}
        </label>
      )}
      <select
        id={inputId}
        className={cn('input', error && 'border-red-400', className)}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
