import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

interface CardProps {
  className?: string
  children: ReactNode
}
export function Card({ className, children }: CardProps) {
  return <div className={cn('card p-6', className)}>{children}</div>
}

export function CardHeader({ className, children }: CardProps) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children }: CardProps) {
  return (
    <h3 className={cn('text-base font-semibold text-slate-900', className)}>
      {children}
    </h3>
  )
}

export function StatCard({
  label,
  value,
  sub,
  icon,
  accent,
}: {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
  accent?: 'green' | 'red' | 'yellow' | 'blue' | 'default'
}) {
  const accents = {
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    blue: 'bg-brand-50 border-brand-200',
    default: '',
  }
  return (
    <div className={cn('card p-5', accents[accent ?? 'default'])}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
          {label}
        </span>
        {icon && <span className="text-slate-400">{icon}</span>}
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}
