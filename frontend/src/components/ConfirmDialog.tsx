import { Loader2 } from 'lucide-react'
import { useEffect } from 'react'
import type { ReactNode } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** Style the confirm button as destructive (red). */
  danger?: boolean
  isPending?: boolean
  onConfirm: () => void
  onClose: () => void
  children?: ReactNode
}

/**
 * Minimal accessible confirmation modal.
 *
 * Closes on Escape and on a backdrop click (unless a request is in flight), and
 * moves the initial focus to the confirm button so keyboard users can act
 * immediately.
 */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  isPending = false,
  onConfirm,
  onClose,
  children,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isPending) onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, isPending, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/50"
      onClick={() => {
        if (!isPending) onClose()
      }}
    >
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-label={title}
          className="w-full max-w-md rounded-2xl border border-surface-200 bg-white p-5 shadow-xl dark:border-surface-800 dark:bg-surface-800 sm:p-6"
          onClick={(event) => event.stopPropagation()}
        >
          <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50">{title}</h2>
          {description && (
            <div className="mt-2 text-sm text-surface-600 dark:text-surface-300">{description}</div>
          )}
          {children && <div className="mt-4">{children}</div>}
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-600 hover:bg-surface-100 disabled:opacity-60 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-700"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              autoFocus
              onClick={onConfirm}
              disabled={isPending}
              className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60 ${
                danger ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-600 hover:bg-brand-700'
              }`}
            >
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
