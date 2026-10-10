import { useEffect, useRef, useState } from 'react'
import { PhoneCall, Video, X } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { chatSocket } from '@/services/chatSocket'
import { useAuthStore } from '@/stores/authStore'
import type { SocketEvent } from '@/types/platform'

const AUTO_DISMISS_MS = 45000

export default function IncomingCallBanner() {
  const me = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const location = useLocation()
  const [incoming, setIncoming] = useState<{ appointmentId: string; fromName: string } | null>(
    null,
  )
  const pathRef = useRef(location.pathname)
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    pathRef.current = location.pathname
  }, [location.pathname])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    if (!chatSocket.ready()) chatSocket.connect(token)

    const clearTimer = () => {
      if (dismissTimer.current) {
        clearTimeout(dismissTimer.current)
        dismissTimer.current = null
      }
    }

    const unsub = chatSocket.subscribe((event: SocketEvent) => {
      if (event.type === 'call-request') {
        const appointmentId = event.appointment_id
        if (!appointmentId) return
        if (event.from_user_id === me?.id) return
        if (pathRef.current === `/video-call/${appointmentId}`) return
        setIncoming({ appointmentId, fromName: event.from_name ?? '' })
        clearTimer()
        dismissTimer.current = setTimeout(() => setIncoming(null), AUTO_DISMISS_MS)
      } else if (event.type === 'call-end' || event.type === 'call-decline') {
        if (!event.appointment_id) return
        setIncoming((prev) => {
          if (prev && prev.appointmentId === event.appointment_id) {
            clearTimer()
            return null
          }
          return prev
        })
      }
    })

    return () => {
      unsub()
      clearTimer()
    }
  }, [me?.id])

  if (!incoming) return null

  const receive = () => {
    const appointmentId = incoming.appointmentId
    setIncoming(null)
    navigate(`/video-call/${appointmentId}`)
  }

  return (
    <div className="fixed left-4 right-4 top-20 z-50 rounded-2xl border border-surface-200 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-surface-800 sm:left-auto sm:right-4 sm:w-72">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
          <PhoneCall className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-surface-900 dark:text-surface-50">
            Incoming video call
          </p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {incoming.fromName || 'Your appointment participant'}
          </p>
        </div>
        <button
          onClick={() => setIncoming(null)}
          aria-label="Dismiss"
          className="rounded-lg p-1.5 text-slate-500 hover:bg-surface-100 dark:text-slate-400 dark:hover:bg-slate-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <button
        onClick={receive}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
      >
        <Video className="h-4 w-4" /> Receive Video Call
      </button>
    </div>
  )
}