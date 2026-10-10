import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, FileBarChart, Loader2 } from 'lucide-react'
import { useState } from 'react'

import { adminDownloadReport, adminReport } from '@/services/adminService'

const REPORT_TYPES = ['users', 'lawyers', 'appointments', 'complaints', 'revenue'] as const

export default function AdminReportsPage() {
  const [reportType, setReportType] = useState<(typeof REPORT_TYPES)[number]>('users')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-report', reportType],
    queryFn: () => adminReport<Record<string, unknown>>(reportType),
  })

  const downloadMut = useMutation({
    mutationFn: () => adminDownloadReport(reportType),
  })

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
            Generate summaries of platform data.
          </p>
        </div>
        <button
          onClick={() => downloadMut.mutate()}
          disabled={downloadMut.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {downloadMut.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Download PDF
        </button>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {REPORT_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setReportType(t)}
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium ${
              reportType === t
                ? 'bg-brand-600 text-white'
                : 'border border-surface-300 text-surface-600 dark:border-surface-700 dark:text-surface-300'
            }`}
          >
            <FileBarChart className="h-4 w-4" />
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
        {isLoading && (
          <div className="flex justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          </div>
        )}
        {isError && (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            Could not load report.
          </p>
        )}
        {!isLoading && !isError && data && (
          <SummaryTable data={data.summary} />
        )}
      </div>
    </div>
  )
}

function SummaryTable({ data }: { data: Record<string, unknown> }) {
  const { total, ...rest } = data
  const entries: Array<[string, unknown]> = []
  if (total !== undefined) entries.push(['total', total])
  Object.keys(rest).forEach((key) => {
    const val = rest[key]
    if (typeof val === 'object' && val !== null) {
      Object.entries(val as Record<string, unknown>).forEach(([k, v]) => {
        entries.push([`${key.replace('_', ' ')} · ${k.replace('_', ' ')}`, v])
      })
    } else {
      entries.push([key.replace('_', ' '), val])
    }
  })

  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {entries.map(([label, value]) => (
        <div
          key={label}
          className="rounded-xl bg-surface-50 px-4 py-3 dark:bg-surface-900"
        >
          <dt className="break-words text-xs uppercase text-surface-500 dark:text-surface-400">{label}</dt>
          <dd className="mt-1 break-words text-lg font-semibold">{String(value)}</dd>
        </div>
      ))}
      {entries.length === 0 && (
        <p className="text-sm text-surface-500 dark:text-surface-400">No data.</p>
      )}
    </dl>
  )
}
