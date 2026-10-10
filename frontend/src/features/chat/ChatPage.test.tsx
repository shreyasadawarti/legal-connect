import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import ChatPage from '@/features/chat/ChatPage'
import {
  createConversation,
  listConversations,
  listMessages,
  sendMessageApi,
} from '@/services/chatService'
import { useAuthStore } from '@/stores/authStore'
import type { ChatConversation, ChatMessage } from '@/types/platform'

vi.mock('@/services/chatSocket', () => ({
  chatSocket: {
    ready: () => false,
    connect: vi.fn(),
    subscribe: vi.fn(() => () => undefined),
    sendRead: vi.fn(),
    sendTyping: vi.fn(),
    sendText: vi.fn(),
  },
}))
vi.mock('@/services/chatService', () => ({
  listConversations: vi.fn(),
  listMessages: vi.fn(),
  createConversation: vi.fn(),
  sendMessageApi: vi.fn(),
  markConversationRead: vi.fn().mockResolvedValue(undefined),
  deleteConversation: vi.fn(),
  clearConversation: vi.fn(),
}))
vi.mock('@/services/socialService', () => ({ createComplaint: vi.fn() }))
vi.mock('@/services/userService', () => ({
  blockUser: vi.fn(),
  listMyBlocks: vi.fn().mockResolvedValue([]),
  lookupUserByEmail: vi.fn(),
  unblockUser: vi.fn(),
}))

const mockedListConversations = vi.mocked(listConversations)
const mockedListMessages = vi.mocked(listMessages)
const mockedCreateConversation = vi.mocked(createConversation)
const mockedSendMessageApi = vi.mocked(sendMessageApi)

const USER_ID = 'c'.repeat(24)
const LAWYER_ID = 'l'.repeat(24)
const CONV_ID = 'v'.repeat(24)

function conversation(overrides: Partial<ChatConversation> = {}): ChatConversation {
  return {
    id: CONV_ID,
    type: 'direct',
    peers: [{ id: LAWYER_ID, name: 'Ananya Sharma', role: 'lawyer' }],
    peer: { id: LAWYER_ID, name: 'Ananya Sharma', role: 'lawyer' },
    last_message: '',
    unread_count: 0,
    ...overrides,
  }
}

function message(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'm'.repeat(24),
    conversation_id: CONV_ID,
    sender_id: LAWYER_ID,
    recipient_id: USER_ID,
    content: 'Hello from the lawyer',
    message_type: 'text',
    delivered: true,
    is_read: false,
    ...overrides,
  } as ChatMessage
}

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location-search">{location.search}</div>
}

function renderChat(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider client={queryClient}>
        <ChatPage />
        <LocationProbe />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: USER_ID,
        name: 'Test User',
        email: 'user@example.com',
        role: 'user',
        status: 'ACTIVE',
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
    })
    mockedListConversations.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    mockedListMessages.mockResolvedValue({
      items: [],
      has_more: false,
      conversation_id: CONV_ID,
    })
  })

  it('loads the conversation and its history when opened via "Message" (?start)', async () => {
    mockedCreateConversation.mockResolvedValue(conversation())
    mockedListMessages.mockResolvedValue({
      items: [message()],
      has_more: false,
      conversation_id: CONV_ID,
    })

    renderChat(`/chat?start=${LAWYER_ID}`)

    expect(await screen.findByText('Hello from the lawyer')).toBeTruthy()
    expect(mockedCreateConversation).toHaveBeenCalledWith(LAWYER_ID)
    expect(mockedListMessages).toHaveBeenCalledWith(CONV_ID)
  })

  it('shows the lawyer name from the created conversation before the list refetch', async () => {
    mockedCreateConversation.mockResolvedValue(conversation())
    renderChat(`/chat?start=${LAWYER_ID}`)
    expect(await screen.findByText('Ananya Sharma')).toBeTruthy()
  })

  it('consumes the ?start param so a refresh cannot resurrect a deleted chat', async () => {
    mockedCreateConversation.mockResolvedValue(conversation())
    renderChat(`/chat?start=${LAWYER_ID}`)

    await waitFor(() => expect(mockedCreateConversation).toHaveBeenCalledWith(LAWYER_ID))
    await waitFor(() => expect(screen.getByTestId('location-search').textContent).toBe(''))
  })

  it('surfaces a list error instead of claiming there are no conversations', async () => {
    mockedListConversations.mockRejectedValue(new Error('boom'))
    renderChat('/chat')
    expect(await screen.findByText(/could not load conversations/i)).toBeTruthy()
  })

  it('surfaces a failed send and keeps the draft instead of dropping it silently', async () => {
    mockedCreateConversation.mockResolvedValue(conversation())
    mockedSendMessageApi.mockRejectedValue(new Error('boom'))
    renderChat(`/chat?start=${LAWYER_ID}`)

    const input = (await screen.findByPlaceholderText('Type a message…')) as HTMLInputElement
    fireEvent.change(input, { target: { value: 'hello?' } })
    fireEvent.submit(input.closest('form') as HTMLFormElement)

    expect(await screen.findByText(/could not send the message/i)).toBeTruthy()
    expect(input.value).toBe('hello?')
  })
})
