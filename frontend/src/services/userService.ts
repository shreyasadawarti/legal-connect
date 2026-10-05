import api from '@/services/api'
import type { User } from '@/types/user'

export interface ProfileUpdatePayload {
  name?: string
  phone?: string
  preferred_language?: string
  city?: string
  bio?: string
}

export async function getMyProfile(): Promise<User> {
  const { data } = await api.get<User>('/users/me')
  return data
}

export async function updateMyProfile(payload: ProfileUpdatePayload): Promise<User> {
  const { data } = await api.patch<User>('/users/me', payload)
  return data
}

export async function lookupUserByEmail(email: string): Promise<{ id: string; name: string }> {
  const { data } = await api.get<{ id: string; name: string }>('/users/lookup', {
    params: { email },
  })
  return data
}
