import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileText, Loader2, Lock, Share2, Trash2, Upload, Users } from 'lucide-react'
import { useState } from 'react'

import {
  deleteDocument,
  getDownloadUrl,
  listDocuments,
  revokeDocument,
  shareDocument,
  uploadDocument,
} from '@/services/documentService'
import { lookupUserByEmail } from '@/services/userService'
import { useAuthStore } from '@/stores/authStore'
import type { DocumentItem } from '@/types/platform'

function fmtSize(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function fmtDate(iso?: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

function DocumentCard({ document }: { document: DocumentItem }) {
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['documents'] })
  const [shareOpen, setShareOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [shareMsg, setShareMsg] = useState('')
  const isOwner = currentUser?.id === document.owner_id

  const download = useMutation({
    mutationFn: () => getDownloadUrl(document.id),
    onSuccess: (data) => window.open(data.url, '_blank'),
  })
  const share = useMutation({
    mutationFn: async () => {
      const user = await lookupUserByEmail(email.trim())
      return shareDocument(document.id, [user.id])
    },
    onSuccess: () => {
      setShareOpen(false)
      setEmail('')
      setShareMsg('')
      invalidate()
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setShareMsg(err.response?.data?.detail || 'No user found with that email')
    },
  })
  const revoke = useMutation({
    mutationFn: () => {
      const target = document.shared_with[0]
      return revokeDocument(document.id, target ? [target] : [])
    },
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: () => deleteDocument(document.id),
    onSuccess: invalidate,
  })

  const canManage = isOwner

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 shrink-0 text-brand-600" />
            <h3 className="truncate font-semibold">{document.title}</h3>
          </div>
          <p className="mt-1 truncate text-sm text-surface-500 dark:text-surface-400">
            {document.original_name} · {fmtSize(document.size_bytes)}
          </p>
          <p className="text-xs text-surface-400">
            Uploaded {fmtDate(document.created_at)} by {document.owner_name}
          </p>
          {document.shared_with.length > 0 && (
            <p className="mt-1 inline-flex items-center gap-1 text-xs text-brand-600">
              <Users className="h-3.5 w-3.5" /> Shared with {document.shared_with.length} user
              {document.shared_with.length > 1 ? 's' : ''}
            </p>
          )}
        </div>
        <div className="flex shrink-0 flex-col gap-1.5">
          <button
            onClick={() => download.mutate()}
            disabled={download.isPending}
            className="inline-flex items-center justify-center gap-1 rounded-lg bg-brand-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <Download className="h-3.5 w-3.5" /> Download
          </button>
          {shareOpen ? (
            <form
              noValidate
              className="flex flex-col gap-1.5"
              onSubmit={(e) => {
                e.preventDefault()
                share.mutate()
              }}
            >
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Recipient email"
                className="w-44 rounded-lg border border-surface-300 bg-surface-50 px-2 py-1 text-xs outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
              />
              <div className="flex gap-1.5">
                <button
                  type="submit"
                  disabled={share.isPending}
                  className="rounded-lg bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-60"
                >
                  Share
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShareOpen(false)
                    setShareMsg('')
                  }}
                  className="rounded-lg border border-surface-300 px-2.5 py-1 text-xs"
                >
                  Cancel
                </button>
              </div>
              {shareMsg && <p className="text-xs text-red-600">{shareMsg}</p>}
            </form>
          ) : (
            <button
              onClick={() => setShareOpen(true)}
              className="inline-flex items-center justify-center gap-1 rounded-lg border border-surface-300 px-2.5 py-1.5 text-xs hover:bg-surface-100 dark:border-surface-700 dark:hover:bg-surface-700"
            >
              <Share2 className="h-3.5 w-3.5" /> Share
            </button>
          )}
          {document.shared_with.length > 0 && (
            <button
              onClick={() => revoke.mutate()}
              disabled={revoke.isPending}
              className="inline-flex items-center justify-center gap-1 rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs text-amber-700 hover:bg-amber-50 disabled:opacity-60 dark:border-amber-900 dark:text-amber-400 dark:hover:bg-amber-900/30"
            >
              <Lock className="h-3.5 w-3.5" /> Revoke
            </button>
          )}
          {canManage && (
            <button
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
              className="inline-flex items-center justify-center gap-1 rounded-lg border border-red-200 px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50 disabled:opacity-60 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function DocumentsPage() {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [uploadMsg, setUploadMsg] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['documents'],
    queryFn: () => listDocuments(),
  })

  const upload = useMutation({
    mutationFn: () => uploadDocument(file!, title),
    onSuccess: () => {
      setFile(null)
      setTitle('')
      setUploadMsg('')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setUploadMsg(err.response?.data?.detail || 'Upload failed')
    },
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">Documents</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Securely store, share, and download your legal documents.
      </p>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
        <h2 className="flex items-center gap-2 font-semibold">
          <Upload className="h-5 w-5 text-brand-600" /> Upload a document
        </h2>
        {uploadMsg && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {uploadMsg}
          </p>
        )}
        <form
          noValidate
          className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault()
            if (file) upload.mutate()
          }}
        >
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium">File</label>
            <input
              required
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Property deed"
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled={!file || upload.isPending}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {upload.isPending ? 'Uploading…' : 'Upload'}
          </button>
        </form>
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-lg font-semibold">My documents &amp; shared with me</h2>
        {isLoading && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          </div>
        )}
        {isError && (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            Could not load documents.
          </p>
        )}
        {!isLoading && !isError && data && data.items.length === 0 && (
          <p className="rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
            No documents yet. Upload your first document above.
          </p>
        )}
        {!isLoading && !isError && data && data.items.length > 0 && (
          <div className="space-y-3">
            {data.items.map((doc) => (
              <DocumentCard key={doc.id} document={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
