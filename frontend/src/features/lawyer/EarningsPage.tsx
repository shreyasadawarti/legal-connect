import { useQuery } from '@tanstack/react-query'
import { Calendar, IndianRupee, Loader2, Wallet } from 'lucide-react'

import { listAppointments } from '@/services/appointmentService'
import { getMyLawyerProfile } from '@/services/lawyerService'
import type { Appointment, AppointmentStatus } from '@/types/platform'

const STATUS_COLOR: Record<string, string> = {
  CONFIRMED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
}

const EARNINGS_STATUSES: AppointmentStatus[] = ['CONFIRMED', 'COMPLETED']

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

function fmtMoney(value: number) {
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}

interface EarningsRecord {
  appointment: Appointment
  hours: number
  amount: number
}

export default function EarningsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['lawyer-earnings'],
    queryFn: async () => {
      let hourlyRate = 0
      try {
        const profile = await getMyLawyerProfile()
        hourlyRate = profile.hourly_rate ?? 0
      } catch {
        // No profile set up yet; show records at a 0 rate instead of failing.
      }
      const [confirmed, completed] = await Promise.all([
        listAppointments({ status: 'CONFIRMED', page_size: 100 }),
        listAppointments({ status: 'COMPLETED', page_size: 100 }),
      ])
      const appointments = [...confirmed.items, ...completed.items]
        .filter((a) => EARNINGS_STATUSES.includes(a.status))
        .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())
      const records: EarningsRecord[] = appointments.map((appointment) => {
        const start = new Date(appointment.start_time).getTime()
        const end = new Date(appointment.end_time).getTime()
        const hours = Math.max(0, (end - start) / 3_600_000)
        return { appointment, hours, amount: hourlyRate * hours }
      })
      const totalEarnings = records.reduce((sum, r) => sum + r.amount, 0)
      const totalHours = records.reduce((sum, r) => sum + r.hours, 0)
      return { hourlyRate, records, totalEarnings, totalHours }
    },
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">Earnings</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Your earnings are calculated from approved or completed appointments at your hourly rate.
      </p>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}

      {!isLoading && data && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <IndianRupee className="h-4 w-4" /> Total earnings
              </p>
              <p className="mt-1 text-2xl font-bold">{fmtMoney(data.totalEarnings)}</p>
            </div>
            <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <Calendar className="h-4 w-4" /> Total appointments
              </p>
              <p className="mt-1 text-2xl font-bold">{data.records.length}</p>
            </div>
            <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <Wallet className="h-4 w-4" /> Total hours
              </p>
              <p className="mt-1 text-2xl font-bold">
                {data.totalHours.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </p>
            </div>
          </div>

          {data.records.length === 0 ? (
            <p className="mt-8 rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
              No earnings yet. Confirmed or completed appointments will appear here.
            </p>
          ) : (
            <div className="mt-6 space-y-4">
              {data.records.map(({ appointment, hours, amount }) => (
                <div
                  key={appointment.id}
                  className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">{appointment.client_name}</h3>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        STATUS_COLOR[appointment.status] ?? ''
                      }`}
                    >
                      {appointment.status}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                    <Calendar className="h-4 w-4" />
                    {fmtDate(appointment.start_time)}
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                    <div>
                      <p className="text-xs text-surface-400">Hours</p>
                      <p className="font-medium">
                        {hours.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-surface-400">Rate</p>
                      <p className="font-medium">{fmtMoney(data.hourlyRate)}/hour</p>
                    </div>
                    <div>
                      <p className="text-xs text-surface-400">Amount</p>
                      <p className="font-semibold">{fmtMoney(amount)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-surface-400">Appointment</p>
                      <p className="font-medium capitalize">{appointment.category.replace('_', ' ')}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}