import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'

import { adminGetVerificationDocument, adminListLawyers, adminSetLawyerVerification, triggerDownload } from '@/services/adminService'
import type { AdminLawyerItem, LawyerStatus } from '@/types/platform'

const STATUS_COLOR: Record<string, string> = {
  PENDING_VERIFICATION: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  ACTIVE: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  SUSPENDED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

export default function AdminLawyersPage() {
  const [filter, setFilter] = useState<string>('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-lawyers', filter],
    queryFn: () => adminListLawyers({ verification_status: filter || undefined, page_size: 50 }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">Lawyer Management</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Review and verify lawyer profiles.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {['', 'PENDING_VERIFICATION', 'ACTIVE', 'REJECTED', 'SUSPENDED'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-full px-3 py-2 text-xs font-medium ${
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
          Could not load lawyers.
        </p>
      )}

      {!isLoading && !isError && data && (
        <div className="mt-6 space-y-4">
          {data.items.map((l) => (
            <LawyerCard key={l.user_id} lawyer={l} />
          ))}
          {data.items.length === 0 && (
            <p className="rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              No lawyers found.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function LawyerCard({ lawyer }: { lawyer: AdminLawyerItem }) {
  const queryClient = useQueryClient()
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectNote, setRejectNote] = useState('')
  const [proofBusy, setProofBusy] = useState(false)
  const [proofError, setProofError] = useState('')

  const verifyMut = useMutation({
    mutationFn: ({
      id,
      status,
      note,
    }: {
      id: string
      status: LawyerStatus
      note?: string
    }) => adminSetLawyerVerification(id, status, note),
    onSuccess: () => {
      setRejectOpen(false)
      setRejectNote('')
      queryClient.invalidateQueries({ queryKey: ['admin-lawyers'] })
    },
  })

  const openProof = async () => {
    setProofError('')
    setProofBusy(true)
    try {
      const { url, filename } = await adminGetVerificationDocument(lawyer.user_id)
      try {
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        triggerDownload(blob, filename)
      } catch {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setProofError(detail ?? 'Could not load the verification document.')
    } finally {
      setProofBusy(false)
    }
  }

  const applyStatus = (status: LawyerStatus) => {
    if (status === 'REJECTED') {
      verifyMut.mutate({
        id: lawyer.user_id,
        status,
        note: rejectNote.trim() || undefined,
      })
    } else {
      verifyMut.mutate({ id: lawyer.user_id, status })
    }
  }

  const errDetail =
    (verifyMut.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
    undefined

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold break-words">{lawyer.name || 'Unnamed lawyer'}</p>
          <p className="break-all text-sm text-surface-500 dark:text-surface-400">{lawyer.email}</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[lawyer.verification_status] ?? ''}`}
        >
          {lawyer.verification_status.replace('_', ' ')}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-surface-500 dark:text-surface-400">
        <span>{lawyer.city || 'Location not set'}</span>
        <span>{lawyer.categories?.map((c) => c.replace('_', ' ')).join(', ')}</span>
        {lawyer.avg_rating > 0 && <span>{lawyer.avg_rating.toFixed(1)} ★ ({lawyer.rating_count})</span>}
      </div>
      {lawyer.rejection_reason && (
        <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Rejection reason: {lawyer.rejection_reason}
        </p>
      )}
      {lawyer.verification_status === 'PENDING_VERIFICATION' && !lawyer.verification_document_id && (
        <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
          Awaiting documentary proof.
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {lawyer.verification_document_id && (
          <button
            disabled={proofBusy || verifyMut.isPending}
            onClick={openProof}
            className="rounded-lg border border-surface-300 px-3 py-1.5 text-sm text-surface-600 hover:bg-surface-100 disabled:opacity-60 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-700"
          >
            {proofBusy ? 'Loading…' : 'View proof'}
          </button>
        )}
        {lawyer.verification_status !== 'ACTIVE' && (
          <button
            disabled={verifyMut.isPending}
            onClick={() => applyStatus('ACTIVE')}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            Approve
          </button>
        )}
        {lawyer.verification_status !== 'REJECTED' && (
          <button
            disabled={verifyMut.isPending}
            onClick={() => setRejectOpen((v) => !v)}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-60 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
          >
            Reject
          </button>
        )}
        {lawyer.verification_status !== 'SUSPENDED' && (
          <button
            disabled={verifyMut.isPending}
            onClick={() => applyStatus('SUSPENDED')}
            className="rounded-lg border border-surface-300 px-3 py-1.5 text-sm text-surface-600 disabled:opacity-60 dark:border-surface-700 dark:text-surface-300"
          >
            Suspend
          </button>
        )}
      </div>

      {errDetail && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">{errDetail}</p>}
      {proofError && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">{proofError}</p>}

      {rejectOpen && (
        <div className="mt-4 space-y-3 rounded-xl bg-surface-50 p-4 dark:bg-surface-900">
          <textarea
            value={rejectNote}
            onChange={(e) => setRejectNote(e.target.value)}
            rows={2}
            placeholder="Rejection reason (required)"
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
          <div className="flex gap-2">
            <button
              disabled={verifyMut.isPending}
              onClick={() => applyStatus('REJECTED')}
              className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
            >
              Confirm Reject
            </button>
            <button
              onClick={() => setRejectOpen(false)}
              className="rounded-lg border border-surface-300 px-3 py-1.5 text-sm dark:border-surface-700"
            >
              Cancel
            </button>
          </div>
          {errDetail && <p className="text-xs text-red-600">{errDetail}</p>}
        </div>
      )}
    </div>
  )
}