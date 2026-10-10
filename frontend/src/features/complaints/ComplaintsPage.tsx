import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, ShieldAlert } from 'lucide-react'
import { useState } from 'react'

import { createComplaint, listMyComplaints, listReceivedComplaints } from '@/services/socialService'

const STATUS_COLOR: Record<string, string> = {
  OPEN: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  IN_PROGRESS: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  RESOLVED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

export default function ComplaintsPage() {
  const queryClient = useQueryClient()
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [success, setSuccess] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['complaints'],
    queryFn: () => listMyComplaints(),
  })

  const { data: received, isLoading: receivedLoading } = useQuery({
    queryKey: ['complaints', 'received'],
    queryFn: () => listReceivedComplaints(),
  })

  const mutation = useMutation({
    mutationFn: () => createComplaint({ subject, description }),
    onSuccess: () => {
      setSubject('')
      setDescription('')
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['complaints'] })
    },
  })

  return (
    <div>
      <div className="flex items-center gap-2">
        <ShieldAlert className="h-6 w-6 text-brand-600" />
        <h1 className="text-2xl font-bold">Complaints</h1>
      </div>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Report an issue. Our team will review it as soon as possible.
      </p>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
        <h2 className="font-semibold">Submit a complaint</h2>
        {success && (
          <p className="mt-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Complaint submitted successfully.
          </p>
        )}
        {mutation.isError && (
          <p className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            Could not submit your complaint.
          </p>
        )}
        <form
          noValidate
          className="mt-4 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <div>
            <label className="mb-1 block text-sm font-medium">Subject</label>
            <input
              required
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Description</label>
            <textarea
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {mutation.isPending ? 'Submitting…' : 'Submit complaint'}
          </button>
        </form>
      </div>

      <div className="mt-6">
        <h2 className="mb-3 text-lg font-semibold">My complaints</h2>
        {isLoading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          </div>
        )}
        {isError && (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            Could not load complaints.
          </p>
        )}
        {!isLoading && !isError && data && data.items.length === 0 && (
          <p className="rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
            No complaints submitted.
          </p>
        )}
        {!isLoading && !isError && data && data.items.length > 0 && (
          <div className="space-y-3">
            {data.items.map((c) => (
              <div key={c.id} className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="min-w-0 truncate font-semibold">{c.subject}</h3>
                  <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[c.status] ?? ''}`}>
                    {c.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">{c.description}</p>
                {c.admin_note && (
                  <p className="mt-2 rounded-lg bg-surface-50 px-3 py-2 text-sm text-surface-600 dark:bg-surface-900 dark:text-surface-300">
                    <span className="font-medium">Response:</span> {c.admin_note}
                  </p>
                )}
                {c.reporter_response && (
                  <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-sm text-surface-700 dark:bg-brand-900/20 dark:text-surface-200">
                    <span className="font-medium">Admin response:</span> {c.reporter_response}
                    {c.reporter_responded_at && (
                      <span className="ml-1 text-xs text-surface-400 dark:text-surface-500">
                        ({new Date(c.reporter_responded_at).toLocaleDateString()})
                      </span>
                    )}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6">
        <h2 className="mb-3 text-lg font-semibold">Complaints about me</h2>
        {receivedLoading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          </div>
        )}
        {!receivedLoading && received && received.items.length === 0 && (
          <p className="rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
            No complaints about you.
          </p>
        )}
        {!receivedLoading && received && received.items.length > 0 && (
          <div className="space-y-3">
            {received.items.map((c) => (
              <div
                key={c.id}
                className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="min-w-0 truncate font-semibold">{c.subject}</h3>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[c.status] ?? ''}`}
                  >
                    {c.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
                  {c.description}
                </p>
                {c.reported_response && (
                  <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-sm text-surface-700 dark:bg-brand-900/20 dark:text-surface-200">
                    <span className="font-medium">Admin response:</span> {c.reported_response}
                    {c.reported_responded_at && (
                      <span className="ml-1 text-xs text-surface-400 dark:text-surface-500">
                        ({new Date(c.reported_responded_at).toLocaleDateString()})
                      </span>
                    )}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
