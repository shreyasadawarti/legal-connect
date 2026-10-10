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

const STATUS_LABEL: Record<string, string> = {
  OPEN: 'Pending',
  IN_PROGRESS: 'Under Review',
  RESOLVED: 'Resolved',
  REJECTED: 'Rejected',
}

const STATUS_OPTIONS: ComplaintStatus[] = [
  'OPEN',
  'IN_PROGRESS',
  'RESOLVED',
  'REJECTED',
]

function formatWhen(value?: string): string {
  if (!value) return ''
  return ` · ${new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })}`
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

      <div className="mt-6 flex flex-wrap gap-2">
        {['', ...STATUS_OPTIONS].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-full px-3 py-2 text-xs font-medium ${
              filter === s
                ? 'bg-brand-600 text-white'
                : 'border border-surface-300 text-surface-600 dark:border-surface-700 dark:text-surface-300'
            }`}
          >
            {s === '' ? 'All' : STATUS_LABEL[s] ?? s}
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
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<ComplaintStatus>(complaint.status)
  const [reporterResponse, setReporterResponse] = useState(complaint.reporter_response ?? '')
  const [reportedResponse, setReportedResponse] = useState(complaint.reported_response ?? '')

  const hasTarget = Boolean(complaint.target_user_id)

  const respondMut = useMutation({
    mutationFn: () =>
      adminRespondComplaint(complaint.id, {
        status,
        reporterResponse: reporterResponse.trim() || undefined,
        reportedResponse: reportedResponse.trim() || undefined,
      }),
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['admin-complaints'] })
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold break-words">{complaint.subject}</p>
          <p className="text-sm text-surface-500 dark:text-surface-400">
            Reported by {complaint.user_name} ({complaint.user_email})
          </p>
          {complaint.target_user_id && (
            <p className="text-sm text-surface-500 dark:text-surface-400">
              Reported user: {complaint.target_user_name || complaint.target_user_id}
              {complaint.target_user_email ? ` (${complaint.target_user_email})` : ''}
            </p>
          )}
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[complaint.status] ?? ''}`}
        >
          {STATUS_LABEL[complaint.status] ?? complaint.status}
        </span>
      </div>
      <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{complaint.description}</p>
      <p className="mt-1 text-xs text-surface-400 dark:text-surface-500">
        {complaint.category ? `Reason: ${complaint.category} · ` : ''}
        {new Date(complaint.created_at).toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        })}
      </p>
      {complaint.admin_note && (
        <p className="mt-2 rounded-lg bg-surface-100 px-3 py-2 text-xs text-surface-500 dark:bg-surface-900 dark:text-surface-400">
          Admin note: {complaint.admin_note}
        </p>
      )}

      {complaint.reporter_response && (
        <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-surface-600 dark:bg-brand-900/20 dark:text-surface-300">
          <span className="font-medium">To reporter ({complaint.user_name}):</span>{' '}
          {complaint.reporter_response}
          <span className="text-surface-400 dark:text-surface-500">
            {formatWhen(complaint.reporter_responded_at)}
          </span>
        </p>
      )}
      {complaint.reported_response && (
        <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-surface-600 dark:bg-brand-900/20 dark:text-surface-300">
          <span className="font-medium">To reported user:</span> {complaint.reported_response}
          <span className="text-surface-400 dark:text-surface-500">
            {formatWhen(complaint.reported_responded_at)}
          </span>
        </p>
      )}

      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="mt-4 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
        >
          Respond
        </button>
      )}

      {open && (
        <div className="mt-4 space-y-3 rounded-xl bg-surface-50 p-4 dark:bg-surface-900">
          <div>
            <label className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300">
              Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as ComplaintStatus)}
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300">
              Response to reporter ({complaint.user_name})
            </label>
            <textarea
              value={reporterResponse}
              onChange={(e) => setReporterResponse(e.target.value)}
              rows={2}
              placeholder="Message the person who filed the complaint"
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          {hasTarget && (
            <div>
              <label className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300">
                Response to reported user ({complaint.target_user_name || 'user'})
              </label>
              <textarea
                value={reportedResponse}
                onChange={(e) => setReportedResponse(e.target.value)}
                rows={2}
                placeholder="Message the person who was reported"
                className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
          )}
          {respondMut.isError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
              Could not save the response.
            </p>
          )}
          <div className="flex gap-2">
            <button
              disabled={respondMut.isPending}
              onClick={() => respondMut.mutate()}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {respondMut.isPending ? 'Saving…' : 'Save response'}
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
