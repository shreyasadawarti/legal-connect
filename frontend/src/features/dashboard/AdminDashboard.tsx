import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/authStore'
import { Loader2 } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { adminAnalytics, adminDashboard } from '@/services/adminService'

const CARD_STYLE =
  'rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800'

export default function AdminDashboard() {
  const user = useAuthStore((s) => s.user)

  const statsQuery = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: () => adminDashboard(),
  })

  const analyticsQuery = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: () => adminAnalytics(),
  })

  const stats = statsQuery.data
  const analytics = analyticsQuery.data

  const statCards = [
    { label: 'Users', value: stats?.total_users ?? 0 },
    { label: 'Lawyers', value: stats?.total_lawyers ?? 0 },
    { label: 'Appointments', value: stats?.total_appointments ?? 0 },
    { label: 'Open Complaints', value: stats?.open_complaints ?? 0 },
    { label: 'Pending Verifications', value: stats?.pending_verifications ?? 0 },
    { label: 'Revenue', value: `$${Number(stats?.total_revenue ?? 0).toLocaleString()}` },
  ]

  const appointmentsByStatus = analytics
    ? Object.entries(analytics.appointments_by_status).map(([name, count]) => ({
        name,
        count,
      }))
    : []

  const loading = statsQuery.isLoading || analyticsQuery.isLoading

  return (
    <div>
      <h1 className="text-2xl font-bold">Admin Dashboard</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Oversee lawyers, users, complaints, and platform activity.
      </p>

      {loading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}

      {statsQuery.isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load dashboard data.
        </p>
      )}

      {!loading && !statsQuery.isError && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {statCards.map((stat) => (
              <div key={stat.label} className={CARD_STYLE}>
                <p className="text-sm text-surface-500 dark:text-surface-400">{stat.label}</p>
                <p className="mt-1 text-2xl font-bold">{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className={CARD_STYLE}>
              <h2 className="text-lg font-semibold">Appointments by status</h2>
              {appointmentsByStatus.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={appointmentsByStatus} margin={{ top: 16, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-300, #d4d4d8)" />
                    <XAxis dataKey="name" fontSize={11} />
                    <YAxis allowDecimals={false} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="mt-4 text-sm text-surface-500 dark:text-surface-400">
                  No appointment data yet.
                </p>
              )}
            </div>

            <div className={CARD_STYLE}>
              <h2 className="text-lg font-semibold">Top practice areas</h2>
              {analytics?.top_categories && analytics.top_categories.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart
                    data={analytics.top_categories}
                    margin={{ top: 16, right: 8, left: -16, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" />
                    <XAxis dataKey="category" fontSize={11} />
                    <YAxis allowDecimals={false} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="mt-4 text-sm text-surface-500 dark:text-surface-400">
                  No category data yet.
                </p>
              )}
            </div>
          </div>
        </>
      )}

      <p className="mt-6 text-sm text-surface-500 dark:text-surface-400">
        Signed in as {user?.email}
      </p>
    </div>
  )
}
