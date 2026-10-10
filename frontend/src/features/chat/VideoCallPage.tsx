import { useEffect, useRef, useState } from 'react'
import { Loader2, Mic, MicOff, PhoneOff, Video, VideoOff, Volume2 } from 'lucide-react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ZegoExpressEngine } from 'zego-express-engine-webrtc'

import { getAppointment } from '@/services/appointmentService'
import { chatSocket } from '@/services/chatSocket'
import { getVideoToken } from '@/services/videoService'
import { useAuthStore } from '@/stores/authStore'

type ZegoLocalStream = Awaited<ReturnType<ZegoExpressEngine['createZegoStream']>>

async function tryRestoreRealAudio(
  localStream: ZegoLocalStream,
): Promise<MediaStreamTrack | null> {
  const stream = localStream.stream
  if (!stream) return null
  try {
    const ms = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    const fresh = ms.getAudioTracks()[0]
    if (!fresh) {
      ms.getTracks().forEach((t) => t.stop())
      return null
    }
    stream.getAudioTracks().forEach((t) => stream.removeTrack(t))
    stream.addTrack(fresh)
    return fresh
  } catch {
    return null
  }
}

export default function VideoCallPage() {
  const navigate = useNavigate()
  const { appointmentId: pathAppointmentId } = useParams()
  const [params] = useSearchParams()
  const userId = useAuthStore((s) => s.user?.id)
  const role = useAuthStore((s) => s.user?.role)

  const appointmentId = pathAppointmentId ?? params.get('appointment') ?? ''
  const queryPeerName = params.get('peerName')

  const localRef = useRef<HTMLVideoElement | null>(null)
  const remoteRef = useRef<HTMLVideoElement | null>(null)
  const zgRef = useRef<ZegoExpressEngine | null>(null)
  const localStreamRef = useRef<ZegoLocalStream | null>(null)
  const streamIdRef = useRef('')
  const hasRemoteRef = useRef(false)

  const [peerName, setPeerName] = useState(queryPeerName ?? 'Peer')
  const [status, setStatus] = useState('Connecting…')
  const [callEnded, setCallEnded] = useState(false)
  const [micOff, setMicOff] = useState(false)
  const [camOff, setCamOff] = useState(false)
  const [mediaError, setMediaError] = useState('')
  const [audioBlocked, setAudioBlocked] = useState(false)
  const [micLabel, setMicLabel] = useState('')

  useEffect(() => {
    if (queryPeerName || !appointmentId) return
    let cancelled = false
    getAppointment(appointmentId)
      .then((appt) => {
        if (cancelled) return
        const peer = userId && appt.lawyer_id === userId ? appt.client_name : appt.lawyer_name
        setPeerName(peer || 'Peer')
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [appointmentId, queryPeerName, userId])

  useEffect(() => {
    if (!appointmentId) {
      setStatus('Missing appointment for this call')
      setCallEnded(true)
      return
    }

    let cancelled = false

    const fail = (message: string) => {
      setStatus(message)
      setCallEnded(true)
    }

    const playRemote = (el: HTMLVideoElement) => {
      el.muted = false
      el.volume = 1
      el.play()
        .then(() => {
          if (!cancelled) setAudioBlocked(false)
        })
        .catch(() => {
          if (!cancelled) setAudioBlocked(true)
        })
    }

    const init = async () => {
      setStatus('Requesting camera…')

      let tokenInfo: Awaited<ReturnType<typeof getVideoToken>>
      try {
        tokenInfo = await getVideoToken(appointmentId)
      } catch (err) {
        if (cancelled) return
        const code = (err as { response?: { status?: number } })?.response?.status
        if (code === 400) fail('Video calls are only available for confirmed appointments')
        else if (code === 403 || code === 404) fail('You are not part of this appointment')
        else if (code === 503) fail('Video calling is not configured on the server')
        else fail('Could not start the video call')
        return
      }
      if (cancelled) return

      const zg = new ZegoExpressEngine(tokenInfo.app_id, '')
      zgRef.current = zg
      const myStreamId = `${tokenInfo.room_id}_${tokenInfo.user_id}`
      streamIdRef.current = myStreamId

      zg.on('roomStateUpdate', (_roomID, state, errorCode) => {
        if (cancelled) return
        if (state === 'DISCONNECTED' && errorCode) {
          setStatus('Connection lost')
        } else if (state === 'CONNECTED' && !hasRemoteRef.current) {
          setStatus('Waiting for peer…')
        }
      })

      zg.on('roomStreamUpdate', (_roomID, updateType, streamList) => {
        if (cancelled) return
        if (updateType === 'ADD') {
          streamList
            .filter((s) => s.streamID !== myStreamId)
            .forEach((s) => {
              zg.startPlayingStream(s.streamID)
                .then((ms) => {
                  if (cancelled) {
                    zg.stopPlayingStream(s.streamID)
                    return
                  }
                  if (remoteRef.current) {
                    remoteRef.current.srcObject = ms
                    playRemote(remoteRef.current)
                  }
                  hasRemoteRef.current = true
                  setStatus('Connected')
                })
                .catch(() => undefined)
            })
        } else {
          streamList.forEach((s) => zg.stopPlayingStream(s.streamID))
          if (remoteRef.current) remoteRef.current.srcObject = null
          hasRemoteRef.current = false
          setAudioBlocked(false)
          if (!cancelled) setStatus('Waiting for peer…')
        }
      })

      setStatus('Joining…')
      let joined = false
      try {
        joined = await zg.loginRoom(tokenInfo.room_id, tokenInfo.token, {
          userID: tokenInfo.user_id,
          userName: tokenInfo.user_name,
        }, { userUpdate: true })
      } catch {
        joined = false
      }
      if (cancelled) return
      if (!joined) {
        fail('Could not join the call room')
        return
      }

      // Ring the other participant of this appointment now that we are in the
      // room. Reuses the chat WebSocket; the server resolves the peer and only
      // notifies a participant of a confirmed appointment.
      const socketToken = localStorage.getItem('access_token')
      if (chatSocket.ready()) {
        chatSocket.startCall(appointmentId)
      } else if (socketToken) {
        chatSocket.connect(socketToken, () => chatSocket.startCall(appointmentId))
      }

      let localStream: ZegoLocalStream
      try {
        localStream = await zg.createZegoStream({ camera: { video: true, audio: true } })
      } catch (err) {
        if (cancelled) return
        const code = (err as { code?: unknown })?.code
        if (code === 1103064 || code === 1103061) {
          fail(
            'Camera and microphone permission was denied. Allow access in your browser settings and reopen this link.',
          )
        } else if (code === 1103065) {
          fail(
            'Your camera or microphone is busy in another application. Close it and reopen this call link.',
          )
        } else {
          setMediaError(
            'Could not access camera/microphone. You can still join and see the other participant.',
          )
          setStatus('Waiting for peer…')
        }
        return
      }
      if (cancelled) {
        zg.destroyStream(localStream)
        return
      }
      localStreamRef.current = localStream
      if (localRef.current && localStream.stream) {
        localRef.current.srcObject = localStream.stream
      }

      const audioTracks = localStream.getAudioTracks()
      const hasRealTrack = audioTracks.some((t) => t.label)
      if (!hasRealTrack) {
        const fresh = await tryRestoreRealAudio(localStream)
        if (fresh) {
          setMicLabel(`Mic: ${fresh.label}`)
          fresh.addEventListener('mute', () => {
            if (cancelled) return
            setMediaError(
              'Your microphone is muted by the system. Allow the microphone in your OS settings so others can hear you.',
            )
          })
          fresh.addEventListener('unmute', () => {
            if (cancelled) return
            setMediaError('')
          })
        } else {
          setMediaError(
            'Microphone not detected — the other participant will not hear you. Check your microphone settings.',
          )
        }
      } else {
        const track = audioTracks.find((t) => t.label)!
        setMicLabel(`Mic: ${track.label}`)
        if (!track.enabled) track.enabled = true
        if (track.muted) {
          setMediaError(
            'Your microphone is muted by the system. Allow the microphone in your OS settings so others can hear you.',
          )
        }
        track.addEventListener('mute', () => {
          if (cancelled) return
          setMediaError(
            'Your microphone is muted by the system. Allow the microphone in your OS settings so others can hear you.',
          )
        })
        track.addEventListener('unmute', () => {
          if (cancelled) return
          setMediaError('')
        })
      }

      zg.startPublishingStream(myStreamId, localStream)
      setStatus('Waiting for peer…')
    }

    init()

    return () => {
      cancelled = true
      if (chatSocket.ready()) chatSocket.endCall(appointmentId)
      const zg = zgRef.current
      const localStream = localStreamRef.current
      if (zg) {
        if (localStream && streamIdRef.current) zg.stopPublishingStream(streamIdRef.current)
        if (localStream) zg.destroyStream(localStream)
        zg.logoutRoom()
        zg.destroyEngine()
      }
      zgRef.current = null
      localStreamRef.current = null
      hasRemoteRef.current = false
    }
  }, [appointmentId])

  const toggleMic = () => {
    if (!zgRef.current || !localStreamRef.current) return
    const next = !micOff
    zgRef.current.muteMicrophone(next)
    setMicOff(next)
  }

  const toggleCam = () => {
    if (!zgRef.current || !localStreamRef.current) return
    const next = !camOff
    zgRef.current.mutePublishStreamVideo(localStreamRef.current, next)
    setCamOff(next)
  }

  const enableSound = () => {
    if (remoteRef.current) {
      remoteRef.current.muted = false
      remoteRef.current.volume = 1
      remoteRef.current.play()
        .then(() => setAudioBlocked(false))
        .catch(() => setAudioBlocked(true))
    }
  }

  const goBack = () => {
    if (window.history.state && (window.history.state as { idx?: number }).idx) {
      navigate(-1)
    } else if (role === 'lawyer') {
      navigate('/lawyer/appointments')
    } else if (role === 'user') {
      navigate('/appointments')
    } else {
      navigate('/')
    }
  }

  const endCall = () => {
    setStatus('Call ended')
    setCallEnded(true)
    goBack()
  }

  if (callEnded) {
    return (
      <div className="flex h-[calc(100dvh-6.5rem)] flex-col items-center justify-center rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800 sm:h-[calc(100dvh-7.5rem)]">
        <p className="text-2xl font-semibold">{status}</p>
        <button
          onClick={goBack}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-white hover:bg-brand-700"
        >
          Back
        </button>
      </div>
    )
  }

  const connecting =
    status === 'Connecting…' || status === 'Requesting camera…' || status === 'Joining…'

  return (
    <div className="space-y-4">
      <div className="relative grid gap-4 md:grid-cols-2">
        <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-2xl border border-surface-200 bg-surface-900 dark:border-slate-700">
          <video
            ref={remoteRef}
            autoPlay
            playsInline
            muted={false}
            className="h-full w-full object-cover"
          />
          <span className="absolute bottom-2 left-2 max-w-[80%] truncate rounded bg-black/50 px-2 py-0.5 text-xs text-white">
            {peerName}
          </span>
          {audioBlocked && (
            <button
              onClick={enableSound}
              className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-black/60 text-white hover:bg-black/50"
            >
              <Volume2 className="h-8 w-8" />
              <span className="text-sm font-medium">Tap to enable sound</span>
            </button>
          )}
        </div>
        <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-2xl border border-surface-200 bg-surface-900 dark:border-slate-700">
          <video ref={localRef} autoPlay playsInline muted className="h-full w-full object-cover" />
          <span className="absolute bottom-2 left-2 rounded bg-black/50 px-2 py-0.5 text-xs text-white">
            You
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800">
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
          {connecting ? (
            <span className="flex items-center gap-2 text-center text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> {status}
            </span>
          ) : (
            <span className="text-center text-sm text-slate-500 dark:text-slate-400">{status}</span>
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
        {micLabel && (
          <p className="mt-1 text-center text-[11px] text-slate-400 dark:text-slate-500">
            {micOff ? `${micLabel} (muted)` : micLabel}
          </p>
        )}
      </div>
    </div>
  )
}
