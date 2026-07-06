import { Loader2 } from 'lucide-react'

export function Spinner({ size = 20, className = '' }: { size?: number; className?: string }) {
  return <Loader2 className={`animate-spin text-brand-500 ${className}`} size={size} />
}

export function FullPageSpinner() {
  return (
    <div className="flex items-center justify-center h-screen">
      <Spinner size={36} />
    </div>
  )
}
