import api from '@/services/api'
import type { LawyerProfile, Paged } from '@/types/platform'

export interface LawyerSearchParams {
  q?: string
  category?: string
  city?: string
  min_rating?: number
  verified_only?: boolean
  page?: number
  page_size?: number
}

export async function searchLawyers(params: LawyerSearchParams = {}): Promise<Paged<LawyerProfile>> {
  const { data } = await api.get<Paged<LawyerProfile>>('/lawyers', { params })
  return data
}

export async function getLawyerProfile(userId: string): Promise<LawyerProfile> {
  const { data } = await api.get<LawyerProfile>(`/lawyers/${userId}`)
  return data
}

export async function getMyLawyerProfile(): Promise<LawyerProfile> {
  const { data } = await api.get<LawyerProfile>('/lawyers/me/profile')
  return data
}

export async function createMyLawyerProfile(payload: Partial<LawyerProfile>): Promise<LawyerProfile> {
  const { data } = await api.put<LawyerProfile>('/lawyers/me/profile', payload)
  return data
}

export async function updateMyLawyerProfile(payload: Partial<LawyerProfile>): Promise<LawyerProfile> {
  const { data } = await api.patch<LawyerProfile>('/lawyers/me/profile', payload)
  return data
}

export async function linkVerificationDocument(documentId: string): Promise<LawyerProfile> {
  const { data } = await api.put<LawyerProfile>('/lawyers/me/verification-document', {
    document_id: documentId,
  })
  return data
}

export async function getLegalCategories(): Promise<{ name: string; label: string; description: string }[]> {
  const { data } = await api.get('/legal-categories')
  return data
}
