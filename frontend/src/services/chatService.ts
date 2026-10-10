import api from '@/services/api'
import type { ChatConversation, ChatMessage, MessageList, Paged } from '@/types/platform'

export async function listConversations(page = 1): Promise<Paged<ChatConversation>> {
  const { data } = await api.get<Paged<ChatConversation>>('/conversations', {
    params: { page },
  })
  return data
}

export async function createConversation(
  otherUserId: string,
  initialMessage?: string,
): Promise<ChatConversation> {
  const { data } = await api.post<ChatConversation>('/conversations', {
    other_user_id: otherUserId,
    initial_message: initialMessage || undefined,
  })
  return data
}

export async function listMessages(
  conversationId: string,
  before?: string,
): Promise<MessageList> {
  const { data } = await api.get<MessageList>(`/messages/${conversationId}`, {
    params: before ? { before } : {},
  })
  return data
}

export async function sendMessageApi(
  conversationId: string,
  content: string,
): Promise<ChatMessage> {
  const { data } = await api.post<ChatMessage>(`/messages/${conversationId}`, { content })
  return data
}

export async function markConversationRead(conversationId: string): Promise<void> {
  await api.post(`/messages/${conversationId}/read`)
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await api.delete(`/conversations/${conversationId}`)
}

export async function clearConversation(conversationId: string): Promise<void> {
  await api.post(`/conversations/${conversationId}/clear`)
}
