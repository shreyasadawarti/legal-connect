import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getMyLawyerProfile } from '@/services/lawyerService'
import { listAppointments } from '@/services/appointmentService'
import { useAuthStore } from '@/stores/authStore'

export default function LawyerDashboard() {
  const user = useAuthStore((s) => s.user)

  const { data: profile } = useQuery({
    queryKey: ['my-lawyer-profile'],
    queryFn: getMyLawyerProfile,
  })

  const { data: pending } = useQuery({
    queryKey: ['lawyer-appointments', 'pending'],
    queryFn: () => listAppointments({ status: 'PENDING' }),
  })

  const pendingCount = pending?.total ?? 0

  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome, {user?.name}</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Your practice overview.
      </p>

      {profile && !profile.bio && (
        <div className="mt-4 flex items-center justify-between rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 dark:border-amber-900 dark:bg-amber-900/20">
          <p className="text-sm text-amber-800 dark:text-amber-300">
            Complete your lawyer profile to be found by clients.
          </p>
          <Link
            to="/lawyer/profile"
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            Set up
          </Link>
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
          <p className="text-sm text-surface-500 dark:text-surface-400">Pending requests</p>
          <p className="mt-1 text-2xl font-bold">{pendingCount}</p>
        </div>
        <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
          <p className="text-sm text-surface-500 dark:text-surface-400">Verification status</p>
          <p className="mt-1 text-lg font-bold">{profile?.verification_status ?? '—'}</p>
        </div>
        <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
          <p className="text-sm text-surface-500 dark:text-surface-400">Categories</p>
          <p className="mt-1 text-2xl font-bold">{profile?.categories?.length ?? 0}</p>
        </div>
      </div>
    </div>
  )
}
