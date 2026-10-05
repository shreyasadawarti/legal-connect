import { useQuery } from '@tanstack/react-query'
import { Loader2, User } from 'lucide-react'

import { adminAuditLogs } from '@/services/adminService'

export default function AdminAuditLogsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-audit-logs'],
    queryFn: () => adminAuditLogs({ page_size: 100 }),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
        Could not load audit logs.
      </p>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Audit Logs</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        A record of important administrative actions.
      </p>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-200 text-xs uppercase text-surface-500 dark:border-surface-700 dark:text-surface-400">
            <tr>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity</th>
              <th className="px-4 py-3">Entity ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
            {data.items.map((item) => (
              <tr key={item.id}>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5">
                    <User className="h-3.5 w-3.5 text-surface-400" />
                    {item.actor_name || item.actor_id || '—'}
                  </span>
                </td>
                <td className="px-4 py-3 font-medium text-brand-700 dark:text-brand-400">
                  {item.action}
                </td>
                <td className="px-4 py-3 capitalize">{item.entity_type}</td>
                <td className="px-4 py-3 text-surface-500 dark:text-surface-400">
                  {item.entity_id || '—'}
                </td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-surface-500">
                  No audit logs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
