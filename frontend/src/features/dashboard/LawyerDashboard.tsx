import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Calendar,
  CalendarCheck,
  CheckCircle2,
  FolderOpen,
  IndianRupee,
  Loader2,
  MessageSquare,
  RefreshCw,
  Star,
  TrendingUp,
  UserCog,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { useLawyerEarnings } from '@/features/lawyer/useLawyerEarnings'
import {
  confirmAppointment,
  listAppointments,
  rejectAppointment,
} from '@/services/appointmentService'
import { getMyLawyerProfile } from '@/services/lawyerService'
import { listNotifications } from '@/services/notificationService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment } from '@/types/platform'

const CARD_STYLE =
  'rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function fmtMoney(value: number) {
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const QUICK_ACTIONS = [
  {
    to: '/lawyer/appointments',
    icon: Calendar,
    title: 'Appointments',
    subtitle: 'Accept or decline new requests',
    cta: 'Review',
  },
  {
    to: '/lawyer/availability',
    icon: CalendarCheck,
    title: 'Availability',
    subtitle: 'Set the hours clients can book',
    cta: 'Manage',
  },
  {
    to: '/lawyer/earnings',
    icon: IndianRupee,
    title: 'Earnings',
    subtitle: 'Earned and projected revenue',
    cta: 'View',
  },
  {
    to: '/lawyer/chat',
    icon: MessageSquare,
    title: 'Messages',
    subtitle: 'Talk to your clients',
    cta: 'Open',
  },
  {
    to: '/lawyer/documents',
    icon: FolderOpen,
    title: 'Documents',
    subtitle: 'Share files securely',
    cta: 'Open',
  },
  {
    to: '/lawyer/profile',
    icon: UserCog,
    title: 'Profile',
    subtitle: 'Bio, rates and practice areas',
    cta: 'Edit',
  },
]

function AppointmentRow({
  appointment,
  onConfirm,
  onReject,
  pending,
}: {
  appointment: Appointment
  onConfirm?: () => void
  onReject?: () => void
  pending?: boolean
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="truncate font-medium">{appointment.client_name}</p>
        <p className="text-sm text-surface-500 dark:text-surface-400">
          {fmtDate(appointment.start_time)} ·{' '}
          <span className="capitalize">{appointment.category.replace('_', ' ')}</span>
        </p>
      </div>
      {onConfirm && onReject && (
        <div className="flex gap-2">
          <button
            type="button"
            disabled={pending}
            onClick={onConfirm}
            className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <CheckCircle2 className="h-3.5 w-3.5" /> Accept
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={onReject}
            className="inline-flex items-center gap-1 rounded-lg border border-surface-300 px-3 py-1.5 text-xs font-medium dark:border-surface-700"
          >
            Decline
          </button>
        </div>
      )}
    </li>
  )
}

export default function LawyerDashboard() {
  const user = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()

  const { data: profile, isLoading: profileLoading, isError: profileError } = useQuery({
    queryKey: ['my-lawyer-profile'],
    queryFn: getMyLawyerProfile,
  })

  // A child key of ['lawyer-appointments'], so accepting, declining or completing an
  // appointment from the appointments page invalidates this dashboard too.
  const {
    data: appointments,
    isLoading: apptsLoading,
    isError: apptsError,
  } = useQuery({
    queryKey: ['lawyer-appointments', 'dashboard'],
    queryFn: () => listAppointments({ page_size: 100 }),
  })

  const { data: notifications } = useQuery({
    queryKey: ['notifications', 'recent'],
    queryFn: () => listNotifications(1),
  })

  const { earnings, isError: earningsError } = useLawyerEarnings()
  // Earnings are a secondary panel, so a failure degrades those two tiles instead of
  // replacing the whole dashboard, but it must not read as still-loading.
  const earningsSub = earnings
    ? null
    : earningsError
      ? 'Unavailable'
      : 'Loading earnings…'

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['lawyer-appointments'] })
    queryClient.invalidateQueries({ queryKey: ['lawyer-earnings'] })
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  const acceptMutation = useMutation({
    mutationFn: (id: string) => confirmAppointment(id),
    onSuccess: invalidate,
  })
  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectAppointment(id),
    onSuccess: invalidate,
  })

  const all = appointments?.items ?? []
  const byStartAsc = (a: Appointment, b: Appointment) =>
    new Date(a.start_time).getTime() - new Date(b.start_time).getTime()

  const pendingList = all.filter((a) => a.status === 'PENDING').sort(byStartAsc)
  const upcoming = all.filter((a) => a.status === 'CONFIRMED').sort(byStartAsc)
  const completed = all
    .filter((a) => a.status === 'COMPLETED')
    .sort((a, b) => byStartAsc(b, a))

  const statCards = [
    {
      label: 'Earned',
      value: earnings ? fmtMoney(earnings.totalRealized) : '—',
      sub: earnings ? `${earnings.realized.length} completed` : earningsSub,
      icon: IndianRupee,
      to: '/lawyer/earnings',
    },
    {
      label: 'Projected',
      value: earnings ? fmtMoney(earnings.totalProjected) : '—',
      sub: earnings ? `${earnings.projected.length} confirmed` : earningsSub,
      icon: TrendingUp,
      to: '/lawyer/earnings',
    },
    {
      label: 'Pending requests',
      value: appointments ? pendingList.length : '—',
      sub: 'Awaiting your response',
      icon: RefreshCw,
      to: '/lawyer/appointments',
    },
    {
      label: 'Upcoming',
      value: appointments ? upcoming.length : '—',
      sub: 'Confirmed sessions',
      icon: CalendarCheck,
      to: '/lawyer/appointments',
    },
    {
      label: 'Completed',
      value: appointments ? completed.length : '—',
      sub: 'All time',
      icon: CheckCircle2,
      to: '/lawyer/appointments',
    },
    {
      label: 'Rating',
      value: profile ? profile.avg_rating.toFixed(1) : '—',
      sub: profile ? `${profile.rating_count} review${profile.rating_count === 1 ? '' : 's'}` : 'Loading',
      icon: Star,
      to: '/lawyer/profile',
    },
  ]

  const isLoading = profileLoading || apptsLoading
  // Appointments drive nearly every panel here, so a failure must be surfaced rather
  // than rendering every tile as a silent em dash.
  const isError = apptsError || profileError
  const recentActivity = (notifications?.items ?? []).slice(0, 5)

  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome, {user?.name}</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Your practice overview.
      </p>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}

      {isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load dashboard data.
        </p>
      )}

      {!isLoading && !isError && (
        <>
          {profile && !profile.bio && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 dark:border-amber-900 dark:bg-amber-900/20">
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

          {profile?.rejection_reason && (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 dark:border-red-900 dark:bg-red-900/20">
              <p className="text-sm font-semibold text-red-800 dark:text-red-300">
                Verification was not approved
              </p>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                {profile.rejection_reason}
              </p>
            </div>
          )}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {statCards.map(({ label, value, sub, icon: Icon, to }) => (
              <Link
                key={label}
                to={to}
                className={`${CARD_STYLE} transition hover:shadow-md`}
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm text-surface-500 dark:text-surface-400">{label}</p>
                  <Icon className="h-4 w-4 text-brand-600" />
                </div>
                <p className="mt-1 text-2xl font-bold">{value}</p>
                <p className="mt-1 text-xs text-surface-400">{sub}</p>
              </Link>
            ))}
          </div>

          <section className="mt-8">
            <h2 className="text-lg font-semibold">Quick actions</h2>
            <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {QUICK_ACTIONS.map(({ to, icon: Icon, title, subtitle, cta }) => (
                <Link
                  key={to}
                  to={to}
                  className={`${CARD_STYLE} transition hover:shadow-md`}
                >
                  <Icon className="h-7 w-7 text-brand-600" />
                  <h3 className="mt-3 font-semibold">{title}</h3>
                  <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
                    {subtitle}
                  </p>
                  <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600">
                    {cta} <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
              ))}
            </div>
          </section>

          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <section className={CARD_STYLE}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Pending requests</h2>
                <Link
                  to="/lawyer/appointments"
                  className="text-sm font-medium text-brand-600 hover:underline"
                >
                  View all
                </Link>
              </div>
              {pendingList.length === 0 ? (
                <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
                  No requests waiting on you.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-surface-200 dark:divide-surface-700">
                  {pendingList.slice(0, 5).map((a) => (
                    <AppointmentRow
                      key={a.id}
                      appointment={a}
                      pending={
                        acceptMutation.isPending || rejectMutation.isPending
                      }
                      onConfirm={() => acceptMutation.mutate(a.id)}
                      onReject={() => rejectMutation.mutate(a.id)}
                    />
                  ))}
                </ul>
              )}
            </section>

            <section className={CARD_STYLE}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Upcoming consultations</h2>
                <Link
                  to="/lawyer/appointments"
                  className="text-sm font-medium text-brand-600 hover:underline"
                >
                  View all
                </Link>
              </div>
              {upcoming.length === 0 ? (
                <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
                  Nothing scheduled yet.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-surface-200 dark:divide-surface-700">
                  {upcoming.slice(0, 5).map((a) => (
                    <AppointmentRow key={a.id} appointment={a} />
                  ))}
                </ul>
              )}
            </section>

            <section className={CARD_STYLE}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Recently completed</h2>
                <Link
                  to="/lawyer/earnings"
                  className="text-sm font-medium text-brand-600 hover:underline"
                >
                  Earnings
                </Link>
              </div>
              {completed.length === 0 ? (
                <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
                  No completed consultations yet.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-surface-200 dark:divide-surface-700">
                  {completed.slice(0, 5).map((a) => (
                    <AppointmentRow key={a.id} appointment={a} />
                  ))}
                </ul>
              )}
            </section>

            <section className={CARD_STYLE}>
              <h2 className="text-lg font-semibold">Recent activity</h2>
              {recentActivity.length === 0 ? (
                <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
                  Nothing new right now.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-surface-200 dark:divide-surface-700">
                  {recentActivity.map((n) => (
                    <li key={n.id} className="py-3">
                      <p className="font-medium">{n.title}</p>
                      <p className="text-sm text-surface-500 dark:text-surface-400">
                        {n.message}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {profile && (
            <section className={`mt-6 ${CARD_STYLE}`}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Profile &amp; verification</h2>
                <Link
                  to="/lawyer/profile"
                  className="text-sm font-medium text-brand-600 hover:underline"
                >
                  Edit
                </Link>
              </div>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-surface-500 dark:text-surface-400">Status</dt>
                  <dd className="font-medium">{profile.verification_status}</dd>
                </div>
                <div>
                  <dt className="text-surface-500 dark:text-surface-400">Verified badge</dt>
                  <dd className="font-medium">{profile.is_verified ? 'Yes' : 'No'}</dd>
                </div>
                <div>
                  <dt className="text-surface-500 dark:text-surface-400">Practice areas</dt>
                  <dd className="font-medium">{profile.categories.length}</dd>
                </div>
                <div>
                  <dt className="text-surface-500 dark:text-surface-400">Hourly rate</dt>
                  <dd className="font-medium">
                    {profile.hourly_rate > 0
                      ? `${fmtMoney(profile.hourly_rate)}/hr`
                      : 'Not set'}
                  </dd>
                </div>
              </dl>
            </section>
          )}
        </>
      )}
    </div>
  )
}
