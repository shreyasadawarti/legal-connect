import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

import { adminListComplaints, adminRespondComplaint } from '@/services/adminService'
import type { AdminComplaintItem, ComplaintStatus } from '@/types/platform'

const STATUS_COLOR: Record<string, string> = {
  OPEN: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  IN_PROGRESS: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  RESOLVED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  REJECTED: 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300',
}

export default function AdminComplaintsPage() {
  const [filter, setFilter] = useState<string>('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-complaints', filter],
    queryFn: () => adminListComplaints({ complaint_status: filter || undefined, page_size: 50 }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">Complaints</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Review and resolve user complaints.
      </p>

      <div className="mt-6 flex gap-2">
        {['', 'OPEN', 'IN_PROGRESS', 'RESOLVED', 'REJECTED'].map((s) => (
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
          Could not load complaints.
        </p>
      )}

      {!isLoading && !isError && data && (
        <div className="mt-6 space-y-4">
          {data.items.map((c) => (
            <ComplaintCard key={c.id} complaint={c} />
          ))}
          {data.items.length === 0 && (
            <p className="rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              No complaints found.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function ComplaintCard({ complaint }: { complaint: AdminComplaintItem }) {
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [open, setOpen] = useState(false)

  const respondMut = useMutation({
    mutationFn: ({ status }: { status: ComplaintStatus }) =>
      adminRespondComplaint(complaint.id, status, note || undefined),
    onSuccess: () => {
      setOpen(false)
      setNote('')
      queryClient.invalidateQueries({ queryKey: ['admin-complaints'] })
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{complaint.subject}</p>
          <p className="text-sm text-surface-500 dark:text-surface-400">
            {complaint.user_name} ({complaint.user_email})
          </p>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[complaint.status] ?? ''}`}
        >
          {complaint.status.replace('_', ' ')}
        </span>
      </div>
      <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{complaint.description}</p>
      {complaint.admin_note && (
        <p className="mt-2 rounded-lg bg-surface-100 px-3 py-2 text-xs text-surface-500 dark:bg-surface-900 dark:text-surface-400">
          Admin note: {complaint.admin_note}
        </p>
      )}

      {complaint.status !== 'RESOLVED' && complaint.status !== 'REJECTED' && !open && (
        <button
          onClick={() => setOpen(true)}
          className="mt-4 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
        >
          Respond
        </button>
      )}

      {open && (
        <div className="mt-4 space-y-3 rounded-xl bg-surface-50 p-4 dark:bg-surface-900">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Admin note (optional)"
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
          <div className="flex gap-2">
            <button
              disabled={respondMut.isPending}
              onClick={() => respondMut.mutate({ status: 'RESOLVED' })}
              className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-60"
            >
              Resolve
            </button>
            <button
              disabled={respondMut.isPending}
              onClick={() => respondMut.mutate({ status: 'REJECTED' })}
              className="rounded-lg border border-surface-300 px-3 py-1.5 text-sm disabled:opacity-60 dark:border-surface-700"
            >
              Reject
            </button>
            <button
              onClick={() => setOpen(false)}
              className="rounded-lg border border-surface-300 px-3 py-1.5 text-sm dark:border-surface-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
