import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Search } from 'lucide-react'
import { useState } from 'react'

import { adminListUsers, adminSetUserStatus } from '@/services/adminService'
import type { Paged } from '@/types/platform'
import type { AdminUserItem, UserStatus } from '@/types/platform'

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  SUSPENDED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  DEACTIVATED: 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300',
}

export default function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-users', search, page],
    queryFn: () => adminListUsers({ q: search || undefined, page, page_size: 20 }),
  })

  const statusMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: UserStatus }) =>
      adminSetUserStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">User Management</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        View accounts and suspend or reactivate users.
      </p>

      <div className="mt-6 flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3 py-2 dark:border-surface-700 dark:bg-surface-800">
        <Search className="h-4 w-4 text-surface-400" />
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          placeholder="Search by name or email"
          className="w-full bg-transparent text-sm outline-none"
        />
      </div>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}
      {isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load users.
        </p>
      )}

      {!isLoading && !isError && data && (
        <AdminUsersTable data={data} onToggle={statusMut} pending={statusMut.isPending} />
      )}
    </div>
  )
}

function AdminUsersTable({
  data,
  onToggle,
  pending,
}: {
  data: Paged<AdminUserItem>
  onToggle: {
    mutate: (v: { id: string; status: UserStatus }) => void
    isPending: boolean
  }
  pending: boolean
}) {
  return (
    <div className="mt-6 overflow-hidden rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-surface-200 text-xs uppercase text-surface-500 dark:border-surface-700 dark:text-surface-400">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
          {data.items.map((u) => (
            <tr key={u.id}>
              <td className="px-4 py-3 font-medium">{u.name}</td>
              <td className="px-4 py-3 text-surface-600 dark:text-surface-300">{u.email}</td>
              <td className="px-4 py-3 capitalize">{u.role}</td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[u.status] ?? ''}`}
                >
                  {u.status}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                {u.role !== 'admin' && (
                  <button
                    disabled={pending}
                    onClick={() =>
                      onToggle.mutate({
                        id: u.id,
                        status: u.status === 'SUSPENDED' ? 'ACTIVE' : 'SUSPENDED',
                      })
                    }
                    className="rounded-lg border border-surface-300 px-3 py-1.5 text-xs font-medium disabled:opacity-60 dark:border-surface-700"
                  >
                    {u.status === 'SUSPENDED' ? 'Reactivate' : 'Suspend'}
                  </button>
                )}
              </td>
            </tr>
          ))}
          {data.items.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-surface-500">
                No users found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
