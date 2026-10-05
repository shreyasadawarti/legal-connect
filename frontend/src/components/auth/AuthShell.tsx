import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Scale } from 'lucide-react'

export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="mx-auto flex min-h-[80vh] max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <Link to="/" className="mb-4 inline-flex items-center gap-2 text-lg font-bold text-brand-700 dark:text-brand-400">
          <Scale className="h-6 w-6" />
          Legal Connect
        </Link>
        <h1 className="mt-3 text-2xl font-bold">{title}</h1>
        <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{subtitle}</p>
      </div>
      {children}
      {footer && <div className="mt-6 text-center text-sm text-surface-600 dark:text-surface-300">{footer}</div>}
    </div>
  )
}
