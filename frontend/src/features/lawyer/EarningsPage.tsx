import { Calendar, IndianRupee, Loader2, TrendingUp, Wallet } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useLawyerEarnings, type EarningsRecord } from '@/features/lawyer/useLawyerEarnings'

const STATUS_COLOR: Record<string, string> = {
  CONFIRMED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

function fmtMoney(value: number) {
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}

function fmtHours(hours: number) {
  return hours.toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

const CARD_STYLE =
  'rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800'

function RecordRow({ record, hourlyRate }: { record: EarningsRecord; hourlyRate: number }) {
  const { appointment, hours, amount } = record
  return (
    <div className={CARD_STYLE}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="truncate font-semibold">{appointment.client_name}</h3>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
            STATUS_COLOR[appointment.status] ?? ''
          }`}
        >
          {appointment.status === 'COMPLETED' ? 'Completed' : 'Confirmed'}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
        <Calendar className="h-4 w-4" />
        {fmtDate(appointment.start_time)}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <div>
          <p className="text-xs text-surface-400">Hours</p>
          <p className="font-medium">{fmtHours(hours)}</p>
        </div>
        <div>
          <p className="text-xs text-surface-400">Rate</p>
          <p className="font-medium">{fmtMoney(hourlyRate)}/hour</p>
        </div>
        <div>
          <p className="text-xs text-surface-400">Amount</p>
          <p className="font-semibold">{fmtMoney(amount)}</p>
        </div>
        <div>
          <p className="text-xs text-surface-400">Appointment</p>
          <p className="font-medium capitalize">
            {appointment.category.replace('_', ' ')}
          </p>
        </div>
      </div>
    </div>
  )
}

export default function EarningsPage() {
  const { earnings, isLoading } = useLawyerEarnings()

  return (
    <div>
      <h1 className="text-2xl font-bold">Earnings</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Earnings are derived from your appointments at your hourly rate. Completed
        appointments count as earned; confirmed appointments count as projected until you
        mark them complete.
      </p>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}

      {!isLoading && earnings && (
        <>
          {!earnings.hasRate && (
            <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-200">
              <p className="font-medium">Set your hourly rate to see earnings figures.</p>
              <p className="mt-1">
                Appointments are listed below, but amounts stay at zero until your profile
                has an hourly rate.
              </p>
              <Link
                to="/lawyer/profile"
                className="mt-3 inline-block rounded-lg bg-brand-600 px-3 py-2 text-white hover:bg-brand-700"
              >
                Update hourly rate
              </Link>
            </div>
          )}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className={CARD_STYLE}>
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <IndianRupee className="h-4 w-4" /> Earned
              </p>
              <p className="mt-1 text-2xl font-bold">{fmtMoney(earnings.totalRealized)}</p>
              <p className="mt-1 text-xs text-surface-400">
                From {earnings.realized.length} completed appointment
                {earnings.realized.length === 1 ? '' : 's'}
              </p>
            </div>
            <div className={CARD_STYLE}>
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <TrendingUp className="h-4 w-4" /> Projected
              </p>
              <p className="mt-1 text-2xl font-bold">{fmtMoney(earnings.totalProjected)}</p>
              <p className="mt-1 text-xs text-surface-400">
                From {earnings.projected.length} confirmed appointment
                {earnings.projected.length === 1 ? '' : 's'}
              </p>
            </div>
            <div className={CARD_STYLE}>
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <Calendar className="h-4 w-4" /> Appointments
              </p>
              <p className="mt-1 text-2xl font-bold">
                {earnings.realized.length + earnings.projected.length}
              </p>
            </div>
            <div className={CARD_STYLE}>
              <p className="flex items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
                <Wallet className="h-4 w-4" /> Total hours
              </p>
              <p className="mt-1 text-2xl font-bold">{fmtHours(earnings.totalHours)}</p>
            </div>
          </div>

          <section className="mt-8">
            <h2 className="text-lg font-semibold">Earned</h2>
            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
              Completed appointments.
            </p>
            {earnings.realized.length === 0 ? (
              <p className="mt-4 rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                Nothing earned yet. Mark a confirmed appointment as complete once the
                consultation is done.
              </p>
            ) : (
              <div className="mt-4 space-y-4">
                {earnings.realized.map((record) => (
                  <RecordRow
                    key={record.appointment.id}
                    record={record}
                    hourlyRate={earnings.hourlyRate}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="mt-8">
            <h2 className="text-lg font-semibold">Projected</h2>
            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
              Confirmed appointments that have not been completed yet.
            </p>
            {earnings.projected.length === 0 ? (
              <p className="mt-4 rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
                No confirmed appointments scheduled.
              </p>
            ) : (
              <div className="mt-4 space-y-4">
                {earnings.projected.map((record) => (
                  <RecordRow
                    key={record.appointment.id}
                    record={record}
                    hourlyRate={earnings.hourlyRate}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
