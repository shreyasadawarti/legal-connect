import { SOCKET_URL } from '@/lib/config'
import type { SocketEvent } from '@/types/platform'

type Listener = (event: SocketEvent) => void

export class ChatSocket {
  private ws: WebSocket | null = null
  private listeners: Set<Listener> = new Set()
  private shouldReconnect = true
  private reconnectDelay = 1000
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private token = ''
  private onOpenCallback: (() => void) | null = null

  connect(token: string, onOpen?: () => void): void {
    this.token = token
    this.onOpenCallback = onOpen ?? null
    this.shouldReconnect = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    const prev = this.ws
    if (prev && prev.readyState !== WebSocket.CLOSED) {
      prev.onmessage = null
      prev.onclose = null
      prev.onerror = null
      prev.close()
    }
    this.ws = null
    this.open()
  }

  private open(): void {
    try {
      const url = `${SOCKET_URL}/api/v1/ws?token=${encodeURIComponent(this.token)}`
      this.ws = new WebSocket(url)
    } catch {
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.reconnectDelay = 1000
      const cb = this.onOpenCallback
      this.onOpenCallback = null
      if (cb) cb()
    }

    this.ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data) as SocketEvent
        this.listeners.forEach((cb) => cb(data))
      } catch {
        // ignore malformed frames
      }
    }

    this.ws.onclose = () => {
      if (this.shouldReconnect) this.scheduleReconnect()
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (this.shouldReconnect) this.open()
    }, this.reconnectDelay)
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 15000)
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  ready(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  send(payload: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload))
    }
  }

  sendText(conversationId: string, content: string): void {
    this.send({ type: 'text', conversation_id: conversationId, content })
  }

  sendTyping(conversationId: string): void {
    this.send({ type: 'typing', conversation_id: conversationId })
  }

  sendRead(conversationId: string): void {
    this.send({ type: 'read', conversation_id: conversationId })
  }

  sendSignaling(
    type: 'call-request' | 'offer' | 'answer' | 'ice' | 'call-decline' | 'call-end',
    conversationId: string,
    extra: Record<string, unknown> = {},
  ): void {
    this.send({ type, conversation_id: conversationId, ...extra })
  }

  startCall(appointmentId: string): void {
    this.send({ type: 'call-request', appointment_id: appointmentId })
  }

  endCall(appointmentId: string): void {
    this.send({ type: 'call-end', appointment_id: appointmentId })
  }

  close(): void {
    this.shouldReconnect = false
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }
}

export const chatSocket = new ChatSocket()
