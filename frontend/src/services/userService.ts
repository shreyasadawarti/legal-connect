import api from '@/services/api'
import type { User } from '@/types/user'

export interface ProfileUpdatePayload {
  name?: string
  phone?: string
  preferred_language?: string
  city?: string
  address?: string
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

export async function uploadProfilePicture(file: File): Promise<User> {
  const body = new FormData()
  body.append('file', file)
  const { data } = await api.post<User>('/users/me/profile-picture', body)
  return data
}

export async function removeProfilePicture(): Promise<User> {
  const { data } = await api.delete<User>('/users/me/profile-picture')
  return data
}
