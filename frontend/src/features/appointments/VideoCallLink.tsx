import { Check, Copy, Link2, Send } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createConversation } from '@/services/chatService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment } from '@/types/platform'

export default function VideoCallLink({ appointment }: { appointment: Appointment }) {
  const [copied, setCopied] = useState(false)
  const [failed, setFailed] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const navigate = useNavigate()
  const me = useAuthStore((s) => s.user)

  const url = `${window.location.origin}/video-call/${appointment.id}`

  const copy = async () => {
    const showCopied = () => {
      setCopied(true)
      setFailed(false)
      window.setTimeout(() => setCopied(false), 2000)
    }
    try {
      await navigator.clipboard.writeText(url)
      showCopied()
    } catch {
      try {
        const ta = document.createElement('textarea')
        ta.value = url
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        const ok = document.execCommand('copy')
        ta.remove()
        if (ok) showCopied()
        else setFailed(true)
      } catch {
        setFailed(true)
      }
    }
  }

  const sendViaChat = async () => {
    if (!me || sending) return
    setSending(true)
    setSendError('')
    try {
      // Either party can generate the shared link; the recipient is whoever is
      // not the current user. The conversation is reused if it already exists.
      const peer = me.id === appointment.lawyer_id ? appointment.client_id : appointment.lawyer_id
      await createConversation(peer, url)
      navigate(me.role === 'lawyer' ? '/lawyer/chat' : '/chat')
    } catch {
      setSendError('Could not send the link. You can still copy it above.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mt-3 border-t border-surface-100 pt-3 dark:border-slate-700">
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 shrink-0 text-surface-400" />
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="min-w-0 flex-1 truncate text-xs text-brand-600 hover:underline dark:text-brand-400"
        >
          {url}
        </a>
        <button
          onClick={copy}
          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-surface-300 px-2 py-1 text-xs font-medium hover:bg-surface-100 dark:border-slate-600 dark:hover:bg-slate-700"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-600" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy link
            </>
          )}
        </button>
        <button
          onClick={sendViaChat}
          disabled={sending || !me}
          className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-brand-600 px-2 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          <Send className="h-3.5 w-3.5" />
          {sending ? 'Sending…' : 'Send link via chat'}
        </button>
      </div>
      {failed && (
        <span className="mt-1 block text-xs text-red-500">
          Could not copy — select the link to copy it.
        </span>
      )}
      {sendError && <span className="mt-1 block text-xs text-red-500">{sendError}</span>}
    </div>
  )
}