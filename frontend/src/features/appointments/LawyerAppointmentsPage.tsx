import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, Check, Loader2, X } from 'lucide-react'

import {
  completeAppointment,
  confirmAppointment,
  listAppointments,
  rejectAppointment,
} from '@/services/appointmentService'
import type { Appointment } from '@/types/platform'

const STATUS_COLOR: Record<string, string> = {
  PENDING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  CONFIRMED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  CANCELLED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  NO_SHOW: 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300',
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function Row({ appointment }: { appointment: Appointment }) {
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['lawyer-appointments'] })

  const confirm = useMutation({ mutationFn: () => confirmAppointment(appointment.id), onSuccess: invalidate })
  const reject = useMutation({ mutationFn: () => rejectAppointment(appointment.id), onSuccess: invalidate })
  const complete = useMutation({ mutationFn: () => completeAppointment(appointment.id), onSuccess: invalidate })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{appointment.client_name}</h3>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[appointment.status] ?? ''}`}>
          {appointment.status}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
        <Calendar className="h-4 w-4" />
        {fmtDate(appointment.start_time)} – {fmtDate(appointment.end_time)}
      </div>
      <div className="mt-1 text-sm text-surface-500 dark:text-surface-400">{appointment.category.replace('_', ' ')}</div>
      {appointment.description && (
        <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{appointment.description}</p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {appointment.status === 'PENDING' && (
          <>
            <button
              onClick={() => confirm.mutate()}
              disabled={confirm.isPending || reject.isPending}
              className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-60"
            >
              <Check className="h-4 w-4" /> Confirm
            </button>
            <button
              onClick={() => reject.mutate()}
              disabled={confirm.isPending || reject.isPending}
              className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-60 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
            >
              <X className="h-4 w-4" /> Reject
            </button>
          </>
        )}
        {appointment.status === 'CONFIRMED' && (
          <button
            onClick={() => complete.mutate()}
            disabled={complete.isPending}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {complete.isPending ? 'Marking…' : 'Mark complete'}
          </button>
        )}
      </div>
    </div>
  )
}

export default function LawyerAppointmentsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['lawyer-appointments'],
    queryFn: () => listAppointments(),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">Appointment requests</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Review and manage your consultation requests.
      </p>

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
      {!isLoading && !isError && data && data.items.length === 0 && (
        <p className="mt-8 rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
          No appointment requests yet.
        </p>
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="mt-6 space-y-4">
          {data.items.map((a) => (
            <Row key={a.id} appointment={a} />
          ))}
        </div>
      )}
    </div>
  )
}
