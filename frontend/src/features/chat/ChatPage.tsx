import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Ban,
  Check,
  CheckCheck,
  Eraser,
  Flag,
  Loader2,
  MessageSquare,
  Send,
  ShieldOff,
  Trash2,
  UserPlus,
} from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

import ConfirmDialog from '@/components/ConfirmDialog'
import DropdownMenu from '@/components/DropdownMenu'
import type { DropdownMenuItem } from '@/components/DropdownMenu'
import { chatSocket } from '@/services/chatSocket'
import {
  clearConversation,
  createConversation,
  deleteConversation,
  listConversations,
  listMessages,
  markConversationRead,
  sendMessageApi,
} from '@/services/chatService'
import { createComplaint } from '@/services/socialService'
import { blockUser, listMyBlocks, lookupUserByEmail, unblockUser } from '@/services/userService'
import MessageContent from '@/features/chat/MessageContent'
import { useAuthStore } from '@/stores/authStore'
import type { ChatConversation, ChatMessage, ReportCategory, SocketEvent } from '@/types/platform'

const REPORT_CATEGORIES: { value: ReportCategory; label: string }[] = [
  { value: 'harassment', label: 'Harassment' },
  { value: 'spam', label: 'Spam' },
  { value: 'fake_profile', label: 'Fake profile' },
  { value: 'abuse', label: 'Abuse' },
  { value: 'unprofessional', label: 'Unprofessional behaviour' },
  { value: 'other', label: 'Other' },
]

export default function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [extraConversations, setExtraConversations] = useState<
    Record<string, ChatConversation>
  >({})
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({})
  const [typingPeer, setTypingPeer] = useState<string | null>(null)
  const [newChatOpen, setNewChatOpen] = useState(false)
  const [newChatEmail, setNewChatEmail] = useState('')
  const [newChatError, setNewChatError] = useState('')
  const [confirmAction, setConfirmAction] = useState<'delete' | 'clear' | null>(null)
  const [reportOpen, setReportOpen] = useState(false)
  const [reportCategory, setReportCategory] = useState<ReportCategory>('harassment')
  const [reportDescription, setReportDescription] = useState('')
  const [blockedIds, setBlockedIds] = useState<Set<string>>(new Set())
  const [notice, setNotice] = useState('')
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    data: conversations,
    isLoading: convLoading,
    isError: convError,
    refetch: refetchConversations,
  } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => listConversations(),
  })

  const { data: blockedUsers } = useQuery({
    queryKey: ['my-blocks'],
    queryFn: () => listMyBlocks(),
  })

  useEffect(() => {
    setBlockedIds(new Set((blockedUsers ?? []).map((b) => b.id)))
  }, [blockedUsers])

  const activeConv =
    conversations?.items.find((c) => c.id === activeConvId) ??
    (activeConvId ? extraConversations[activeConvId] : undefined) ??
    null
  const isBlocked = activeConv?.peer ? blockedIds.has(activeConv.peer.id) : false

  const fetchMessages = useCallback((convId: string) => {
    listMessages(convId)
      .then((res) => setMessages((prev) => ({ ...prev, [convId]: res.items })))
      .catch(() => undefined)
  }, [])

  const flashNotice = useCallback((text: string) => {
    setNotice(text)
    window.setTimeout(() => setNotice((cur) => (cur === text ? '' : cur)), 4000)
  }, [])

  const activeMessages = activeConvId ? (messages[activeConvId] ?? []) : []

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    if (!chatSocket.ready()) chatSocket.connect(token)
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
    if (!startId || startId === user?.id) return
    // `?start=` is a one-time "open this chat" intent. Consume it immediately so a
    // later refresh cannot silently recreate (and un-hide) a conversation the user
    // deliberately deleted; reopening is only ever triggered by an explicit action.
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.delete('start')
        return next
      },
      { replace: true },
    )
    createConversation(startId)
      .then((conv) => {
        queryClient.invalidateQueries({ queryKey: ['conversations'] })
        setExtraConversations((prev) => ({ ...prev, [conv.id]: conv }))
        setActiveConvId(conv.id)
        fetchMessages(conv.id)
      })
      .catch(() => undefined)
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
            m.sender_id === user?.id
              ? { ...m, delivered: true, is_read: true }
              : m,
          ),
        }))
        break
      case 'delivered':
        setMessages((prev) => ({
          ...prev,
          [event.conversation_id]: (prev[event.conversation_id] ?? []).map((m) =>
            m.sender_id === user?.id ? { ...m, delivered: true } : m,
          ),
        }))
        break
      case 'typing':
        setTypingPeer(event.user_id)
        if (typingTimeout.current) clearTimeout(typingTimeout.current)
        typingTimeout.current = setTimeout(() => setTypingPeer(null), 2500)
        break
      case 'error':
        flashNotice(event.error || 'Something went wrong. Please try again.')
        break
      default:
        break
    }
  }

  const selectConversation = useCallback(
    (conv: ChatConversation) => {
      setActiveConvId(conv.id)
      // An empty array is still "loaded"; only fetch when we have nothing yet.
      if (messages[conv.id] === undefined) fetchMessages(conv.id)
    },
    [messages, fetchMessages],
  )

  const sendMessage = useCallback(
    (convId: string) => {
      const text = (drafts[convId] ?? '').trim()
      if (!text) return
      setDrafts((prev) => ({ ...prev, [convId]: '' }))
      if (chatSocket.ready()) {
        chatSocket.sendText(convId, text)
      } else {
        sendMessageApi(convId, text)
          .then((msg) =>
            setMessages((prev) => ({
              ...prev,
              [convId]: [...(prev[convId] ?? []), msg],
            })),
          )
          .catch(() => {
            setDrafts((prev) => ({ ...prev, [convId]: text }))
            flashNotice('Could not send the message. Please try again.')
          })
      }
    },
    [drafts, flashNotice],
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
      setExtraConversations((prev) => ({ ...prev, [conv.id]: conv }))
      setActiveConvId(conv.id)
      fetchMessages(conv.id)
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setNewChatError(detail || 'Could not start a chat with that user.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (conversationId: string) => deleteConversation(conversationId),
    onSuccess: (_res, conversationId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setMessages((prev) => {
        const next = { ...prev }
        delete next[conversationId]
        return next
      })
      setActiveConvId((cur) => (cur === conversationId ? null : cur))
      setConfirmAction(null)
    },
    onError: () => {
      setConfirmAction(null)
      flashNotice('Could not delete the chat. Please try again.')
    },
  })

  const clearMutation = useMutation({
    mutationFn: (conversationId: string) => clearConversation(conversationId),
    onSuccess: (_res, conversationId) => {
      setMessages((prev) => ({ ...prev, [conversationId]: [] }))
      setConfirmAction(null)
      flashNotice('Chat history cleared.')
    },
    onError: () => {
      setConfirmAction(null)
      flashNotice('Could not clear the chat. Please try again.')
    },
  })

  const reportMutation = useMutation({
    mutationFn: (payload: {
      subject: string
      description: string
      conversation_id: string
      target_user_id: string
      category: string
    }) => createComplaint(payload),
    onSuccess: () => {
      setReportOpen(false)
      setReportDescription('')
      flashNotice('Report submitted to the admin team.')
    },
    onError: () => flashNotice('Could not submit the report. Please try again.'),
  })

  const toggleBlock = useCallback(async () => {
    const peer = activeConv?.peer
    if (!peer) return
    try {
      if (blockedIds.has(peer.id)) {
        await unblockUser(peer.id)
        setBlockedIds((prev) => {
          const next = new Set(prev)
          next.delete(peer.id)
          return next
        })
        flashNotice(`${peer.name} unblocked.`)
      } else {
        await blockUser(peer.id)
        setBlockedIds((prev) => new Set(prev).add(peer.id))
        flashNotice(`${peer.name} blocked.`)
      }
      queryClient.invalidateQueries({ queryKey: ['my-blocks'] })
    } catch {
      flashNotice('Could not update the block. Please try again.')
    }
  }, [activeConv, blockedIds, flashNotice, queryClient])

  const submitReport = () => {
    const peer = activeConv?.peer
    if (!peer) return
    const description = reportDescription.trim()
    if (!description) return
    const categoryLabel =
      REPORT_CATEGORIES.find((c) => c.value === reportCategory)?.label ?? reportCategory
    reportMutation.mutate({
      subject: `Report ${peer.name}: ${categoryLabel}`,
      description,
      conversation_id: activeConv.id,
      target_user_id: peer.id,
      category: reportCategory,
    })
  }

  const menuItems: DropdownMenuItem[] = activeConv
    ? [
        {
          label: 'Delete Chat',
          icon: Trash2,
          danger: true,
          onClick: () => setConfirmAction('delete'),
        },
        {
          label: 'Clear Chat History',
          icon: Eraser,
          onClick: () => setConfirmAction('clear'),
        },
        {
          label: 'Report User',
          icon: Flag,
          danger: true,
          onClick: () => {
            setReportCategory('harassment')
            setReportDescription('')
            setReportOpen(true)
          },
        },
        {
          label: isBlocked ? 'Unblock User' : 'Block User',
          icon: isBlocked ? ShieldOff : Ban,
          onClick: () => {
            void toggleBlock()
          },
        },
      ]
    : []

  return (
    <div className="grid h-[calc(100dvh-6.5rem)] gap-4 sm:h-[calc(100dvh-7.5rem)] lg:grid-cols-3">
      {/* Conversation list */}
      <div
        className={`${activeConvId ? 'hidden lg:flex' : 'flex'} rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800 lg:col-span-1`}
      >
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
                  className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-surface-900"
                />
                <button
                  type="submit"
                  disabled={startChatMutation.isPending}
                  className="shrink-0 rounded-lg bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700"
                >
                  {startChatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Start'}
                </button>
              </form>
              {newChatError && <p className="mt-2 text-xs text-red-600">{newChatError}</p>}
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {convLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
              </div>
            ) : convError ? (
              <p className="px-4 py-10 text-center text-sm text-red-600 dark:text-red-400">
                Could not load conversations.
              </p>
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
      <div
        className={`${activeConvId ? 'flex' : 'hidden lg:flex'} flex-col rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800 lg:col-span-2`}
      >
        {!activeConv ? (
          <div className="flex flex-1 flex-col items-center justify-center text-slate-400 dark:text-slate-500">
            <MessageSquare className="h-12 w-12" />
            <p className="mt-3 text-sm">Select a conversation to start chatting.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3 dark:border-slate-700">
              <div className="flex min-w-0 items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveConvId(null)}
                  aria-label="Back to conversations"
                  className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-slate-700 lg:hidden"
                >
                  <ArrowLeft className="h-5 w-5" />
                </button>
                <div className="min-w-0">
                  <span className="block truncate font-semibold">{activeConv.peer?.name}</span>
                  {typingPeer === activeConv.peer?.id && (
                    <span className="text-xs text-brand-600 dark:text-brand-400">typing…</span>
                  )}
                </div>
              </div>
              <DropdownMenu items={menuItems} label="Conversation options" />
            </div>

            {notice && (
              <div className="border-b border-brand-100 bg-brand-50 px-4 py-2 text-xs text-brand-700 dark:border-brand-900/40 dark:bg-brand-900/20 dark:text-brand-300">
                {notice}
              </div>
            )}

            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
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
                      <p className="whitespace-pre-wrap break-words">
                        <MessageContent text={m.content} />
                      </p>
                      <div
                        className={`mt-0.5 flex items-center justify-end gap-1 text-[10px] ${mine ? 'text-brand-100' : 'text-slate-500 dark:text-slate-400'}`}
                      >
                        {mine ? (
                          <>
                            {m.created_at && (
                              <span>
                                {new Date(m.created_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </span>
                            )}
                            {m.is_read ? (
                              <CheckCheck
                                className="h-3.5 w-3.5 text-sky-300"
                                aria-label="Read"
                              />
                            ) : m.delivered ? (
                              <CheckCheck className="h-3.5 w-3.5" aria-label="Delivered" />
                            ) : (
                              <Check className="h-3.5 w-3.5" aria-label="Sent" />
                            )}
                          </>
                        ) : m.created_at ? (
                          new Date(m.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        ) : (
                          ''
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
              <div ref={bottomRef} />
            </div>

            {isBlocked && (
              <p className="border-t border-surface-200 px-4 py-2 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                You blocked this user. Unblock them to send messages.
              </p>
            )}

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
                placeholder={isBlocked ? 'Unblock to send messages' : 'Type a message…'}
                disabled={isBlocked}
                className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-60 dark:border-slate-600 dark:bg-surface-900"
              />
              <button
                type="submit"
                disabled={isBlocked}
                className="shrink-0 rounded-xl bg-brand-600 p-2.5 text-white hover:bg-brand-700 disabled:opacity-60"
                aria-label="Send"
              >
                <Send className="h-5 w-5" />
              </button>
            </form>
          </>
        )}
      </div>

      <ConfirmDialog
        open={confirmAction === 'delete'}
        title="Delete chat?"
        description="This hides the conversation and its messages from your inbox only. The other person keeps their copy. A new message will bring it back."
        confirmLabel="Delete"
        danger
        isPending={deleteMutation.isPending}
        onConfirm={() => activeConv && deleteMutation.mutate(activeConv.id)}
        onClose={() => setConfirmAction(null)}
      />

      <ConfirmDialog
        open={confirmAction === 'clear'}
        title="Clear chat history?"
        description="This clears the messages in your view. The other person still sees their copy."
        confirmLabel="Clear"
        isPending={clearMutation.isPending}
        onConfirm={() => activeConv && clearMutation.mutate(activeConv.id)}
        onClose={() => setConfirmAction(null)}
      />

      <ConfirmDialog
        open={reportOpen}
        title="Report user"
        description={`Report ${activeConv?.peer?.name ?? 'this user'} to the admin team.`}
        confirmLabel="Submit report"
        danger
        isPending={reportMutation.isPending}
        onConfirm={submitReport}
        onClose={() => setReportOpen(false)}
      >
        <div className="space-y-3">
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-200">
            Reason
            <select
              value={reportCategory}
              onChange={(e) => setReportCategory(e.target.value as ReportCategory)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-surface-900"
            >
              {REPORT_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-surface-700 dark:text-surface-200">
            Details
            <textarea
              value={reportDescription}
              onChange={(e) => setReportDescription(e.target.value)}
              rows={3}
              placeholder="Describe what happened"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-surface-900"
            />
          </label>
        </div>
      </ConfirmDialog>
    </div>
  )
}
