import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, Loader2, Star } from 'lucide-react'
import { useState } from 'react'

import { cancelAppointment, listAppointments } from '@/services/appointmentService'
import { submitReview } from '@/services/socialService'
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
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function AppointmentCard({ appointment }: { appointment: Appointment }) {
  const queryClient = useQueryClient()
  const [reviewMode, setReviewMode] = useState(false)
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')

  const cancelMut = useMutation({
    mutationFn: () => cancelAppointment(appointment.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['appointments'] }),
  })
  const reviewMut = useMutation({
    mutationFn: () => submitReview(appointment.lawyer_id, rating, comment || undefined),
    onSuccess: () => {
      setReviewMode(false)
      queryClient.invalidateQueries({ queryKey: ['lawyer-reviews'] })
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{appointment.lawyer_name}</h3>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[appointment.status] ?? ''}`}>
          {appointment.status}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
        <Calendar className="h-4 w-4" />
        {fmtDate(appointment.start_time)} – {fmtDate(appointment.end_time)}
      </div>
      <div className="mt-1 text-sm text-surface-500 dark:text-surface-400">{appointment.category.replace('_', ' ')}</div>

      <div className="mt-4 flex flex-wrap gap-2">
        {(appointment.status === 'PENDING' || appointment.status === 'CONFIRMED') && (
          <button
            onClick={() => cancelMut.mutate()}
            disabled={cancelMut.isPending}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-60 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
          >
            {cancelMut.isPending ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
        {appointment.status === 'COMPLETED' && !reviewMode && (
          <button
            onClick={() => setReviewMode(true)}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Leave a review
          </button>
        )}
      </div>

      {reviewMode && (
        <form
          noValidate
          className="mt-4 space-y-3 rounded-xl bg-surface-50 p-4 dark:bg-surface-900"
          onSubmit={(e) => {
            e.preventDefault()
            reviewMut.mutate()
          }}
        >
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                className="text-xl"
                aria-label={`${n} star`}
              >
                <Star className={`h-6 w-6 ${n <= rating ? 'fill-amber-400 text-amber-400' : 'text-surface-300'}`} />
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            placeholder="Share your experience (optional)"
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={reviewMut.isPending}
              className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {reviewMut.isPending ? 'Submitting…' : 'Submit review'}
            </button>
            <button
              type="button"
              onClick={() => setReviewMode(false)}
              className="rounded-lg border border-surface-300 px-4 py-1.5 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

export default function CitizenAppointmentsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['appointments'],
    queryFn: () => listAppointments(),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">My appointments</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Manage your consultations and leave reviews after they complete.
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
          You have no appointments yet.
        </p>
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="mt-6 space-y-4">
          {data.items.map((appointment) => (
            <AppointmentCard key={appointment.id} appointment={appointment} />
          ))}
        </div>
      )}
    </div>
  )
}
