import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

import { adminListAppointments } from '@/services/adminService'
import type { AdminAppointmentItem, Paged } from '@/types/platform'

export const APPOINTMENT_STATUSES = [
  'PENDING',
  'CONFIRMED',
  'COMPLETED',
  'CANCELLED',
  'REJECTED',
] as const

const STATUS_COLOR: Record<string, string> = {
  PENDING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  CONFIRMED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  CANCELLED: 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

export default function AdminAppointmentsPage() {
  const [filter, setFilter] = useState<string>('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-appointments', filter],
    queryFn: () => adminListAppointments({ status: filter || undefined, page_size: 50 }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">Appointments</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Review all appointments across the platform.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {['', ...APPOINTMENT_STATUSES].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium ${
              filter === s
                ? 'bg-brand-600 text-white'
                : 'border border-surface-300 text-surface-600 dark:border-surface-700 dark:text-surface-300'
            }`}
          >
            {s === '' ? 'All' : s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}
      {isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load appointments.
        </p>
      )}

      {!isLoading && !isError && data && (
        <AdminAppointmentsTable data={data} />
      )}
    </div>
  )
}

function AdminAppointmentsTable({ data }: { data: Paged<AdminAppointmentItem> }) {
  return (
    <div className="mt-6 overflow-x-auto rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-surface-200 text-xs uppercase text-surface-500 dark:border-surface-700 dark:text-surface-400">
          <tr>
            <th className="px-4 py-3">Client</th>
            <th className="px-4 py-3">Lawyer</th>
            <th className="px-4 py-3">Category</th>
            <th className="px-4 py-3">Start</th>
            <th className="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
          {data.items.map((a) => (
            <tr key={a.id}>
              <td className="px-4 py-3 font-medium">{a.client_name || '—'}</td>
              <td className="px-4 py-3 text-surface-600 dark:text-surface-300">
                {a.lawyer_name || '—'}
              </td>
              <td className="px-4 py-3 capitalize">{a.category.replace('_', ' ')}</td>
              <td className="px-4 py-3 text-surface-600 dark:text-surface-300">
                {a.start_time ? new Date(a.start_time).toLocaleString() : '—'}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[a.status] ?? ''}`}
                >
                  {a.status.replace('_', ' ')}
                </span>
              </td>
            </tr>
          ))}
          {data.items.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-surface-500">
                No appointments found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
