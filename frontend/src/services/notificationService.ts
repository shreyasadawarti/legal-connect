import api from '@/services/api'
import type { Notification, Paged } from '@/types/platform'

export interface NotificationList extends Paged<Notification> {
  unread: number
}

export async function listNotifications(page = 1): Promise<NotificationList> {
  const { data } = await api.get<NotificationList>('/notifications', { params: { page } })
  return data
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await api.get<{ unread: number }>('/notifications/unread-count')
  return data.unread
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const { data } = await api.patch<Notification>(`/notifications/${id}/read`)
  return data
}

export async function markAllNotificationsRead(): Promise<void> {
  await api.patch('/notifications/read-all')
}

export async function deleteNotification(id: string): Promise<void> {
  await api.delete(`/notifications/${id}`)
}
