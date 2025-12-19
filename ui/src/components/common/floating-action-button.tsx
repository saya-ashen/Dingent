import { type ReactNode } from 'react'

export function FloatingActionButton({ children }: { children: ReactNode }) {
  const baseClasses = 'absolute top-18 z-50 flex flex-row items-center gap-2'

  const positionClass = 'right-5'

  return <div className={`${baseClasses} ${positionClass}`}>{children}</div>
}
