import type { ReactNode } from 'react'

interface Props {
  text: string
  children?: ReactNode
}

export function InfoTooltip({ text, children }: Props) {
  return (
    <span className="group relative inline-flex items-center">
      {children}
      <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-200 text-slate-500 text-[10px] font-semibold cursor-help hover:bg-slate-300 hover:text-slate-700 transition-colors shrink-0">
        i
      </span>
      <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 w-64 px-3 py-2 rounded-lg bg-slate-800 text-white text-xs leading-relaxed shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all pointer-events-none z-[9999]">
        {text}
        <div className="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-slate-800" />
      </div>
    </span>
  )
}
