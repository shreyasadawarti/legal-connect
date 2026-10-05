import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Loader2,
  MessageSquare,
  Send,
  UserPlus,
  Video,
} from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { chatSocket } from '@/services/chatSocket'
import {
  createConversation,
  listConversations,
  listMessages,
  markConversationRead,
  sendMessageApi,
} from '@/services/chatService'
import { lookupUserByEmail } from '@/services/userService'
import { useAuthStore } from '@/stores/authStore'
import type { ChatConversation, ChatMessage, SocketEvent } from '@/types/platform'

export default function ChatPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({})
  const [typingPeer, setTypingPeer] = useState<string | null>(null)
  const [newChatOpen, setNewChatOpen] = useState(false)
  const [newChatEmail, setNewChatEmail] = useState('')
  const [newChatError, setNewChatError] = useState('')
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    data: conversations,
    isLoading: convLoading,
    refetch: refetchConversations,
  } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => listConversations(),
  })

  const activeMessages = activeConvId ? (messages[activeConvId] ?? []) : []

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    chatSocket.connect(token)
    const unsub = chatSocket.subscribe((event: SocketEvent) => {
      handleSocketEvent(event)
    })
    return () => {
      unsub()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeMessages.length, activeConvId])

  useEffect(() => {
    const startId = searchParams.get('start')
    if (startId && startId !== user?.id) {
      createConversation(startId)
        .then((conv) => {
          queryClient.invalidateQueries({ queryKey: ['conversations'] })
          setActiveConvId(conv.id)
          setMessages((prev) => ({ ...prev, [conv.id]: prev[conv.id] ?? [] }))
        })
        .catch(() => undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  useEffect(() => {
    if (activeConvId && messages[activeConvId]?.length) {
      markConversationRead(activeConvId).catch(() => undefined)
      if (chatSocket.ready()) chatSocket.sendRead(activeConvId)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      const conv = conversations?.items.find((c) => c.id === activeConvId)
      if (conv && conv.unread_count > 0) refetchConversations()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConvId])

  const handleSocketEvent = (event: SocketEvent) => {
    switch (event.type) {
      case 'message': {
        const msg = event.message
        setMessages((prev) => {
          const list = prev[msg.conversation_id] ?? []
          if (list.some((m) => m.id === msg.id)) return prev
          return { ...prev, [msg.conversation_id]: [...list, msg] }
        })
        refetchConversations()
        break
      }
      case 'notice':
        refetchConversations()
        break
      case 'read':
        setMessages((prev) => ({
          ...prev,
          [event.conversation_id]: (prev[event.conversation_id] ?? []).map((m) =>
            m.recipient_id !== user?.id ? m : { ...m, is_read: true },
          ),
        }))
        break
      case 'typing':
        setTypingPeer(event.user_id)
        if (typingTimeout.current) clearTimeout(typingTimeout.current)
        typingTimeout.current = setTimeout(() => setTypingPeer(null), 2500)
        break
      default:
        break
    }
  }

  const selectConversation = useCallback(
    (conv: ChatConversation) => {
      setActiveConvId(conv.id)
      if (!messages[conv.id]) {
        listMessages(conv.id).then((res) =>
          setMessages((prev) => ({ ...prev, [conv.id]: res.items })),
        )
      }
    },
    [messages],
  )

  const sendMessage = useCallback(
    (convId: string) => {
      const text = (drafts[convId] ?? '').trim()
      if (!text) return
      if (chatSocket.ready()) {
        chatSocket.sendText(convId, text)
      } else {
        sendMessageApi(convId, text).then((msg) =>
          setMessages((prev) => ({
            ...prev,
            [convId]: [...(prev[convId] ?? []), msg],
          })),
        )
      }
      setDrafts((prev) => ({ ...prev, [convId]: '' }))
    },
    [drafts],
  )

  const handleTyping = (convId: string) => {
    if (chatSocket.ready()) chatSocket.sendTyping(convId)
  }

  const startChatMutation = useMutation({
    mutationFn: async (email: string) => {
      const target = await lookupUserByEmail(email)
      return createConversation(target.id)
    },
    onSuccess: (conv) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setNewChatOpen(false)
      setNewChatEmail('')
      setNewChatError('')
      setActiveConvId(conv.id)
      setMessages((prev) => ({ ...prev, [conv.id]: prev[conv.id] ?? [] }))
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setNewChatError(detail || 'Could not start a chat with that user.')
    },
  })

  const activeConv = conversations?.items.find((c) => c.id === activeConvId) ?? null

  const startCall = () => {
    if (!activeConv || !activeConv.peer) return
    if (chatSocket.ready()) {
      chatSocket.sendSignaling('call-request', activeConv.id, {
        to_user_id: activeConv.peer.id,
      })
    }
    navigate(
      `/chat/video?conversation=${activeConv.id}&peer=${activeConv.peer.id}&peerName=${encodeURIComponent(
        activeConv.peer.name,
      )}`,
    )
  }

  return (
    <div className="grid h-[calc(100vh-7.5rem)] gap-4 lg:grid-cols-3">
      {/* Conversation list */}
      <div className="flex rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800 lg:col-span-1">
        <div className="flex w-full flex-col">
          <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3 dark:border-slate-700">
            <h2 className="font-semibold">Messages</h2>
            <button
              onClick={() => setNewChatOpen((v) => !v)}
              className="rounded-lg p-2 text-slate-500 hover:bg-surface-100 dark:text-slate-300 dark:hover:bg-slate-700"
              aria-label="New chat"
            >
              <UserPlus className="h-5 w-5" />
            </button>
          </div>

          {newChatOpen && (
            <div className="border-b border-surface-200 p-3 dark:border-slate-700">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  if (newChatEmail.trim()) startChatMutation.mutate(newChatEmail.trim())
                }}
                className="flex gap-2"
              >
                <input
                  value={newChatEmail}
                  onChange={(e) => setNewChatEmail(e.target.value)}
                  placeholder="User email"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-surface-900"
                />
                <button
                  type="submit"
                  disabled={startChatMutation.isPending}
                  className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700"
                >
                  {startChatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Start'}
                </button>
              </form>
              {newChatError && <p className="mt-2 text-xs text-red-600">{newChatError}</p>}
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            {convLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
              </div>
            ) : !conversations?.items.length ? (
              <p className="px-4 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
                No conversations yet.
              </p>
            ) : (
              conversations.items.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => selectConversation(conv)}
                  className={`block w-full border-b border-surface-100 px-4 py-3 text-left hover:bg-surface-50 dark:border-slate-700/40 dark:hover:bg-slate-700/40 ${
                    activeConvId === conv.id ? 'bg-brand-50 dark:bg-brand-900/20' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{conv.peer?.name ?? 'Unknown'}</span>
                    {conv.unread_count > 0 && (
                      <span className="rounded-full bg-brand-600 px-2 py-0.5 text-xs font-semibold text-white">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-sm text-slate-500 dark:text-slate-400">
                    {conv.last_message || 'Tap to open'}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Message window */}
      <div className="flex flex-col rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800 lg:col-span-2">
        {!activeConv ? (
          <div className="flex flex-1 flex-col items-center justify-center text-slate-400 dark:text-slate-500">
            <MessageSquare className="h-12 w-12" />
            <p className="mt-3 text-sm">Select a conversation to start chatting.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3 dark:border-slate-700">
              <div>
                <span className="font-semibold">{activeConv.peer?.name}</span>
                {typingPeer === activeConv.peer?.id && (
                  <span className="ml-2 text-xs text-brand-600 dark:text-brand-400">typing…</span>
                )}
              </div>
              <button
                onClick={startCall}
                className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700"
              >
                <Video className="h-4 w-4" /> Call
              </button>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {activeMessages.map((m) => {
                const mine = m.sender_id === user?.id
                return (
                  <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-sm ${
                        mine
                          ? 'bg-brand-600 text-white'
                          : 'bg-surface-100 text-surface-800 dark:bg-slate-700 dark:text-slate-100'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{m.content}</p>
                      <div
                        className={`mt-0.5 text-[10px] ${mine ? 'text-brand-100' : 'text-slate-500 dark:text-slate-400'}`}
                      >
                        {mine
                          ? m.is_read
                            ? 'Read'
                            : 'Sent'
                          : m.created_at
                            ? new Date(m.created_at).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : ''}
                      </div>
                    </div>
                  </div>
                )
              })}
              <div ref={bottomRef} />
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                sendMessage(activeConv.id)
              }}
              className="flex items-center gap-2 border-t border-surface-200 p-3 dark:border-slate-700"
            >
              <input
                value={drafts[activeConv.id] ?? ''}
                onChange={(e) => {
                  setDrafts((prev) => ({ ...prev, [activeConv.id]: e.target.value }))
                  handleTyping(activeConv.id)
                }}
                placeholder="Type a message…"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-surface-900"
              />
              <button
                type="submit"
                className="rounded-xl bg-brand-600 p-2.5 text-white hover:bg-brand-700"
                aria-label="Send"
              >
                <Send className="h-5 w-5" />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
