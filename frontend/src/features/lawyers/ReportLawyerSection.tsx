import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Flag, Loader2, ShieldAlert } from 'lucide-react'
import { useState } from 'react'

import { listAppointments } from '@/services/appointmentService'
import { createComplaint } from '@/services/socialService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment } from '@/types/platform'

/**
 * Lets a citizen report a lawyer they have actually booked. The affordance is hidden
 * entirely for lawyers the citizen has no appointment with, and the submitted
 * appointment id is re-verified server-side before the complaint is stored.
 */
export default function ReportLawyerSection({ lawyerUserId }: { lawyerUserId: string }) {
  const queryClient = useQueryClient()
  const role = useAuthStore((s) => s.user?.role)
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const isCitizen = role === 'user'

  const { data: appointments } = useQuery({
    queryKey: ['appointments', 'eligible-lawyers'],
    queryFn: () => listAppointments({ page_size: 100 }),
    enabled: isCitizen,
    staleTime: 60_000,
  })

  // A child key of ['appointments'], so booking and cancelling already invalidate it.
  const mine = (appointments?.items ?? []).filter((a) => a.lawyer_id === lawyerUserId)

  // The most recent appointment is the strongest context for the report.
  const anchor = mine.reduce<Appointment | undefined>(
    (latest, a) =>
      !latest || new Date(a.start_time).getTime() > new Date(latest.start_time).getTime()
        ? a
        : latest,
    undefined,
  )

  const mutation = useMutation({
    mutationFn: () => {
      if (!anchor) throw new Error('No appointment to report')
      return createComplaint({
        subject: subject.trim(),
        description: description.trim(),
        related_appointment_id: anchor.id,
      })
    },
    onSuccess: () => {
      setSubject('')
      setDescription('')
      setSubmitted(true)
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['complaints'] })
    },
  })

  // No appointment, no complaint option at all.
  if (!isCitizen || !anchor) return null

  if (!open) {
    return (
      <div className="mt-6">
        {submitted && (
          <p className="mb-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Complaint submitted. Our team will review it shortly.
          </p>
        )}
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-300 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50 dark:border-red-900/60 dark:text-red-300 dark:hover:bg-red-900/20"
        >
          <Flag className="h-4 w-4" /> Report this lawyer
        </button>
        <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
          Available because you have an appointment with this lawyer.
        </p>
      </div>
    )
  }

  return (
    <div className="mt-6 rounded-xl border border-red-200 bg-red-50/40 p-4 dark:border-red-900/60 dark:bg-red-900/10">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-red-700 dark:text-red-300">
        <ShieldAlert className="h-4 w-4" /> Report this lawyer
      </h3>
      <p className="mt-1 text-xs text-surface-600 dark:text-surface-400">
        This report is linked to your{' '}
        {new Date(anchor.start_time).toLocaleDateString(undefined, { dateStyle: 'medium' })}{' '}
        appointment. An administrator reviews every complaint.
      </p>

      {mutation.isError && (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not submit your complaint. Please try again.
        </p>
      )}

      <form
        noValidate
        className="mt-3 space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <div>
          <label htmlFor="complaint-subject" className="mb-1 block text-xs font-medium">
            Subject
          </label>
          <input
            id="complaint-subject"
            required
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
        </div>
        <div>
          <label htmlFor="complaint-description" className="mb-1 block text-xs font-medium">
            What happened?
          </label>
          <textarea
            id="complaint-description"
            required
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="mr-1 inline h-3.5 w-3.5 animate-spin" /> Submitting…
              </>
            ) : (
              'Submit complaint'
            )}
          </button>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium dark:border-surface-700"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
