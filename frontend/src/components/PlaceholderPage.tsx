import { Construction } from 'lucide-react'

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center rounded-2xl border border-dashed border-surface-300 text-center dark:border-surface-700">
      <Construction className="h-12 w-12 text-surface-400" />
      <h1 className="mt-4 text-xl font-semibold">{title}</h1>
      <p className="mt-2 max-w-md text-sm text-surface-500 dark:text-surface-400">
        This section is under construction and will be implemented in an upcoming development phase.
      </p>
    </div>
  )
}
