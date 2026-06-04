import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

type AlertType = 'info' | 'success' | 'warning' | 'error'

const styles: Record<AlertType, { wrapper: string; icon: ReactNode }> = {
  info: {
    wrapper: 'bg-blue-50 border-blue-200 text-blue-800',
    icon: <Info size={16} />,
  },
  success: {
    wrapper: 'bg-green-50 border-green-200 text-green-800',
    icon: <CheckCircle size={16} />,
  },
  warning: {
    wrapper: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    icon: <AlertTriangle size={16} />,
  },
  error: {
    wrapper: 'bg-red-50 border-red-200 text-red-800',
    icon: <XCircle size={16} />,
  },
}

export function Alert({
  type = 'info',
  title,
  children,
  className,
}: {
  type?: AlertType
  title?: string
  children: ReactNode
  className?: string
}) {
  const s = styles[type]
  return (
    <div className={cn('flex gap-3 p-4 rounded-lg border text-sm', s.wrapper, className)}>
      <span className="mt-0.5 shrink-0">{s.icon}</span>
      <div>
        {title && <p className="font-medium mb-0.5">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  )
}
