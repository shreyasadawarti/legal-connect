import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar, Loader2 } from 'lucide-react'
import { useState } from 'react'

import { bookAppointment } from '@/services/appointmentService'
import type { LawyerProfile } from '@/types/platform'

export default function BookAppointmentSection({ lawyer }: { lawyer: LawyerProfile }) {
  const queryClient = useQueryClient()
  const [start, setStart] = useState('')
  const [durationMin, setDurationMin] = useState(60)
  const [description, setDescription] = useState('')
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: () => {
      const startDate = new Date(start)
      const endDate = new Date(startDate.getTime() + durationMin * 60000)
      return bookAppointment({
        lawyer_id: lawyer.user_id,
        category: lawyer.categories[0] ?? 'other',
        start_time: startDate.toISOString(),
        end_time: endDate.toISOString(),
        description: description || undefined,
      })
    },
    onSuccess: () => {
      setSuccess(true)
      setStart('')
      setDescription('')
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
    },
  })

  const errorMsg = (mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
      <h3 className="flex items-center gap-2 text-lg font-semibold">
        <Calendar className="h-5 w-5 text-brand-600" /> Book a consultation
      </h3>
      {success && (
        <p className="mt-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
          Appointment requested! The lawyer will confirm your booking.
        </p>
      )}
      {errorMsg && (
        <p className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {errorMsg}
        </p>
      )}
      {!success && (
        <form
          className="mt-4 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <div>
            <label className="mb-1 block text-sm font-medium">Start date &amp; time</label>
            <input
              required
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Duration</label>
            <select
              value={durationMin}
              onChange={(e) => setDurationMin(Number(e.target.value))}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            >
              <option value={30}>30 minutes</option>
              <option value={60}>1 hour</option>
              <option value={90}>1.5 hours</option>
              <option value={120}>2 hours</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Describe your issue (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled={!start || mutation.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Request appointment
          </button>
        </form>
      )}
    </div>
  )
}
