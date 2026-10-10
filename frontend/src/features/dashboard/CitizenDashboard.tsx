import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Calendar, MapPin, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAuthStore } from '@/stores/authStore'
import { listAppointments } from '@/services/appointmentService'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function CitizenDashboard() {
  const user = useAuthStore((s) => s.user)

  const { data } = useQuery({
    queryKey: ['appointments', 'upcoming'],
    queryFn: () => listAppointments({ status: 'CONFIRMED', page_size: 3 }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold break-words">Welcome, {user?.name}</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Manage your legal consultations and documents.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link to="/lawyers" className="rounded-2xl border border-surface-200 bg-white p-5 hover:shadow-md dark:border-surface-800 dark:bg-surface-800">
          <span className="text-2xl">⚖️</span>
          <h3 className="mt-3 font-semibold">Find Lawyers</h3>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">Search verified legal professionals</p>
          <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600">Explore <ArrowRight className="h-4 w-4" /></span>
        </Link>
        <Link to="/appointments" className="rounded-2xl border border-surface-200 bg-white p-5 hover:shadow-md dark:border-surface-800 dark:bg-surface-800">
          <Calendar className="h-7 w-7 text-brand-600" />
          <h3 className="mt-3 font-semibold">Appointments</h3>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">Book and manage consultations</p>
          <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600">View <ArrowRight className="h-4 w-4" /></span>
        </Link>
        <Link to="/ai-assistant" className="rounded-2xl border border-surface-200 bg-white p-5 hover:shadow-md dark:border-surface-800 dark:bg-surface-800">
          <Sparkles className="h-7 w-7 text-brand-600" />
          <h3 className="mt-3 font-semibold">AI Assistant</h3>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">Get AI-powered legal guidance</p>
          <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600">View <ArrowRight className="h-4 w-4" /></span>
        </Link>
        <Link to="/nearby-lawyers" className="rounded-2xl border border-surface-200 bg-white p-5 hover:shadow-md dark:border-surface-800 dark:bg-surface-800">
          <MapPin className="h-7 w-7 text-brand-600" />
          <h3 className="mt-3 font-semibold">Nearby Lawyers</h3>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">Find lawyers on the map</p>
          <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600">Open <ArrowRight className="h-4 w-4" /></span>
        </Link>
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Upcoming consultations</h2>
          <Link to="/appointments" className="text-sm font-medium text-brand-600 hover:underline">
            View all
          </Link>
        </div>
        {!data || data.items.length === 0 ? (
          <div className="rounded-2xl border border-surface-200 bg-white p-6 text-sm text-surface-500 dark:border-surface-800 dark:bg-surface-800 dark:text-surface-400">
            <p>You have no upcoming consultations.</p>
            <Link to="/lawyers" className="mt-2 inline-block font-medium text-brand-600 hover:underline">
              Book a lawyer →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {data.items.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between gap-3 rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.lawyer_name}</p>
                  <p className="truncate text-sm text-surface-500 dark:text-surface-400">{fmtDate(a.start_time)}</p>
                </div>
                <span className="shrink-0 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                  {a.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
