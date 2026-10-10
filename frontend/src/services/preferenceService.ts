import api from '@/services/api'
import type { UserPreferences } from '@/types/platform'

export async function getMyPreferences(): Promise<UserPreferences> {
  const { data } = await api.get<UserPreferences>('/users/me/preferences')
  return data
}

export async function updateMyPreferences(
  patch: Partial<UserPreferences>,
): Promise<UserPreferences> {
  const { data } = await api.patch<UserPreferences>('/users/me/preferences', patch)
  return data
}
