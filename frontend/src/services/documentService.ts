import api from '@/services/api'
import type { DocumentItem, Paged } from '@/types/platform'

export async function uploadDocument(file: File, title: string, shareWithUserId?: string, docType?: string): Promise<DocumentItem> {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (docType) form.append('doc_type', docType)
  if (shareWithUserId) form.append('share_with_user_id', shareWithUserId)
  const { data } = await api.post<DocumentItem>('/documents/upload', form)
  return data
}

export async function listDocuments(page = 1): Promise<Paged<DocumentItem>> {
  const { data } = await api.get<Paged<DocumentItem>>('/documents', { params: { page } })
  return data
}

export async function getDownloadUrl(id: string): Promise<{ url: string; filename: string }> {
  const { data } = await api.get<{ url: string; filename: string }>(`/documents/${id}/download`)
  return data
}

export async function shareDocument(id: string, userIds: string[]): Promise<DocumentItem> {
  const { data } = await api.post<DocumentItem>(`/documents/${id}/share`, { user_ids: userIds })
  return data
}

export async function revokeDocument(id: string, userIds: string[]): Promise<DocumentItem> {
  const { data } = await api.post<DocumentItem>(`/documents/${id}/revoke`, { user_ids: userIds })
  return data
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`)
}
