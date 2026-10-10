import api from '@/services/api'

export interface VideoToken {
  room_id: string
  token: string
  app_id: number
  user_id: string
  user_name: string
  expires_in: number
}

export async function getVideoToken(appointmentId: string): Promise<VideoToken> {
  const { data } = await api.get<VideoToken>(`/appointments/${appointmentId}/video-token`)
  return data
}
