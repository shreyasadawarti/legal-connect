import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Mic, MicOff, PhoneOff, Video, VideoOff } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { chatSocket } from '@/services/chatSocket'
import type { SocketEvent } from '@/types/platform'

const STUN_SERVERS: RTCConfiguration = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
}

export default function VideoCallPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const conversationId = params.get('conversation') ?? ''
  const peerName = params.get('peerName') ?? 'Peer'

  const localRef = useRef<HTMLVideoElement | null>(null)
  const remoteRef = useRef<HTMLVideoElement | null>(null)
  const pcRef = useRef<RTCPeerConnection | null>(null)
  const localStreamRef = useRef<MediaStream | null>(null)
  const statusRef = useRef('connecting')
  const peerIdRef = useRef('')

  const [status, setStatus] = useState('Connecting…')
  const [callEnded, setCallEnded] = useState(false)
  const [micOff, setMicOff] = useState(false)
  const [camOff, setCamOff] = useState(false)
  const [mediaError, setMediaError] = useState('')

  const setStatusSafe = useCallback((s: string) => {
    statusRef.current = s
    setStatus(s)
  }, [])

  const getOrCreatePeerConnection = useCallback(() => {
    if (pcRef.current) return pcRef.current
    const pc = new RTCPeerConnection(STUN_SERVERS)
    pcRef.current = pc
    localStreamRef.current?.getTracks().forEach((track) => {
      pc.addTrack(track, localStreamRef.current!)
    })
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        chatSocket.sendSignaling('ice', conversationId, {
          candidate: JSON.stringify(event.candidate),
        })
      }
    }
    pc.ontrack = (event) => {
      if (remoteRef.current && event.streams[0]) {
        remoteRef.current.srcObject = event.streams[0]
      }
    }
    return pc
  }, [conversationId])

  const handleSocketEvent = useCallback(
    async (event: SocketEvent) => {
      if (event.type === 'call-end' || event.type === 'call-decline') {
        setStatusSafe('Call ended')
        setCallEnded(true)
        hangup()
        return
      }

      if (event.type === 'ice') {
        if (peerIdRef.current && event.from_user_id !== peerIdRef.current) return
        try {
          const candidate = JSON.parse(event.candidate ?? 'null')
          if (candidate) {
            await getOrCreatePeerConnection().addIceCandidate(candidate)
          }
        } catch {
          // ignore malformed candidates
        }
        return
      }

      if (event.type === 'offer') {
        if (peerIdRef.current && event.from_user_id !== peerIdRef.current) return
        peerIdRef.current = event.from_user_id
        const pc = getOrCreatePeerConnection()
        await pc.setRemoteDescription(JSON.parse(event.sdp ?? 'null'))
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        chatSocket.sendSignaling('answer', conversationId, {
          sdp: JSON.stringify(pc.localDescription),
        })
        setStatusSafe('Connected')
        return
      }

      if (event.type === 'answer') {
        if (event.from_user_id !== peerIdRef.current) return
        const pc = getOrCreatePeerConnection()
        if (pc.remoteDescription) return
        await pc.setRemoteDescription(JSON.parse(event.sdp ?? 'null'))
        setStatusSafe('Connected')
        return
      }

      if (event.type === 'call-request') {
        if (peerIdRef.current && event.from_user_id !== peerIdRef.current) return
        peerIdRef.current = event.from_user_id
        const pc = getOrCreatePeerConnection()
        const offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        chatSocket.sendSignaling('offer', conversationId, {
          sdp: JSON.stringify(pc.localDescription),
        })
        setStatusSafe('Calling…')
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conversationId, getOrCreatePeerConnection, setStatusSafe],
  )

  const hangup = useCallback(() => {
    chatSocket.sendSignaling('call-end', conversationId)
    pcRef.current?.close()
    pcRef.current = null
    localStreamRef.current?.getTracks().forEach((t) => t.stop())
    localStreamRef.current = null
  }, [conversationId])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token || !conversationId) {
      setCallEnded(true)
      return
    }
    if (!chatSocket.ready()) chatSocket.connect(token)
    const unsub = chatSocket.subscribe(handleSocketEvent)

    let cancelled = false
    const init = async () => {
      setStatusSafe('Requesting camera…')
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        })
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        localStreamRef.current = stream
        if (localRef.current) localRef.current.srcObject = stream
        setStatusSafe('Calling…')
        setTimeout(() => {
          chatSocket.sendSignaling('call-request', conversationId)
        }, 400)
      } catch {
        if (!cancelled) {
          setMediaError(
            'Could not access camera/microphone. The video call started but your device media was unavailable.',
          )
          setStatusSafe('Calling without media…')
          setTimeout(() => {
            chatSocket.sendSignaling('call-request', conversationId)
          }, 400)
        }
      }
    }
    init()

    return () => {
      cancelled = true
      unsub()
      pcRef.current?.close()
      pcRef.current = null
      localStreamRef.current?.getTracks().forEach((t) => t.stop())
      localStreamRef.current = null
      chatSocket.sendSignaling('call-end', conversationId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, handleSocketEvent])

  const toggleMic = () => {
    const enabled = micOff
    localStreamRef.current?.getAudioTracks().forEach((t) => (t.enabled = enabled))
    setMicOff(!micOff)
  }

  const toggleCam = () => {
    const enabled = camOff
    localStreamRef.current?.getVideoTracks().forEach((t) => (t.enabled = enabled))
    setCamOff(!camOff)
  }

  const endCall = () => {
    hangup()
    setCallEnded(true)
    setStatusSafe('Call ended')
    navigate(-1)
  }

  if (callEnded) {
    return (
      <div className="flex h-[calc(100vh-7.5rem)] flex-col items-center justify-center rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800">
        <p className="text-2xl font-semibold">{status}</p>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-white hover:bg-brand-700"
        >
          Back to chat
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="relative grid gap-4 lg:grid-cols-2">
        <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-2xl border border-surface-200 bg-surface-900 dark:border-slate-700">
          <video ref={remoteRef} autoPlay playsInline className="h-full w-full object-cover" />
          <span className="absolute bottom-2 left-2 rounded bg-black/50 px-2 py-0.5 text-xs text-white">
            {peerName}
          </span>
        </div>
        <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-2xl border border-surface-200 bg-surface-900 dark:border-slate-700">
          <video ref={localRef} autoPlay playsInline muted className="h-full w-full object-cover" />
          <span className="absolute bottom-2 left-2 rounded bg-black/50 px-2 py-0.5 text-xs text-white">
            You
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800">
        <div className="flex items-center justify-center gap-3">
          {status === 'Connecting…' || status === 'Calling…' ? (
            <span className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> {status}
            </span>
          ) : (
            <span className="text-sm text-slate-500 dark:text-slate-400">{status}</span>
          )}

          <button
            onClick={toggleMic}
            className={`rounded-full p-3 ${
              micOff ? 'bg-red-600 text-white' : 'bg-surface-100 text-slate-700 dark:bg-slate-700 dark:text-slate-100'
            }`}
            aria-label="Toggle microphone"
          >
            {micOff ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>
          <button
            onClick={toggleCam}
            className={`rounded-full p-3 ${
              camOff ? 'bg-red-600 text-white' : 'bg-surface-100 text-slate-700 dark:bg-slate-700 dark:text-slate-100'
            }`}
            aria-label="Toggle camera"
          >
            {camOff ? <VideoOff className="h-5 w-5" /> : <Video className="h-5 w-5" />}
          </button>
          <button
            onClick={endCall}
            className="rounded-full bg-red-600 p-3 text-white hover:bg-red-700"
            aria-label="End call"
          >
            <PhoneOff className="h-5 w-5" />
          </button>
        </div>
        {mediaError && (
          <p className="mt-3 text-center text-xs text-amber-600">{mediaError}</p>
        )}
      </div>
    </div>
  )
}
