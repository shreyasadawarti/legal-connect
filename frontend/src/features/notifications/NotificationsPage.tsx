import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCheck, Loader2 } from 'lucide-react'

import { deleteNotification, listNotifications, markAllNotificationsRead, markNotificationRead } from '@/services/notificationService'
import type { Notification } from '@/types/platform'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function NotificationRow({ notification }: { notification: Notification }) {
  const queryClient = useQueryClient()
  const read = useMutation({
    mutationFn: () => markNotificationRead(notification.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const del = useMutation({
    mutationFn: () => deleteNotification(notification.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  return (
    <div
      className={`rounded-2xl border p-4 ${
        notification.is_read
          ? 'border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800'
          : 'border-brand-200 bg-brand-50 dark:border-brand-900 dark:bg-brand-900/20'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
              {notification.type}
            </span>
            {!notification.is_read && (
              <span className="h-2 w-2 rounded-full bg-brand-600" aria-label="Unread" />
            )}
          </div>
          <h3 className="mt-2 font-semibold">{notification.title}</h3>
          <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">{notification.message}</p>
          <p className="mt-2 text-xs text-surface-400">{fmtDate(notification.created_at)}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          {!notification.is_read && (
            <button
              onClick={() => read.mutate()}
              className="rounded-lg border border-surface-300 px-2.5 py-1 text-xs hover:bg-surface-100 dark:border-surface-700 dark:hover:bg-surface-700"
            >
              Mark read
            </button>
          )}
          <button
            onClick={() => del.mutate()}
            className="rounded-lg border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => listNotifications(),
  })
  const markAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Notifications</h1>
          <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
            Updates about your appointments, reviews, and more.
          </p>
        </div>
        {data && data.unread > 0 && (
          <button
            onClick={() => markAll.mutate()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 px-3 py-1.5 text-sm hover:bg-surface-100 dark:border-surface-700 dark:hover:bg-surface-700"
          >
            <CheckCheck className="h-4 w-4" /> Mark all read
          </button>
        )}
      </div>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}
      {isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load notifications.
        </p>
      )}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <div className="mt-8 flex flex-col items-center rounded-2xl bg-surface-100 px-4 py-10 text-surface-500 dark:bg-surface-800 dark:text-surface-400">
          <Bell className="h-8 w-8" />
          <p className="mt-2 text-sm">You're all caught up.</p>
        </div>
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="mt-6 space-y-3">
          {data.items.map((n) => (
            <NotificationRow key={n.id} notification={n} />
          ))}
        </div>
      )}
    </div>
  )
}
