import { useQuery } from '@tanstack/react-query'

import { listAppointments } from '@/services/appointmentService'
import { getMyLawyerProfile } from '@/services/lawyerService'
import type { Appointment } from '@/types/platform'

export interface EarningsRecord {
  appointment: Appointment
  hours: number
  amount: number
}

export interface LawyerEarnings {
  hourlyRate: number
  /** A lawyer with no profile or no rate set cannot have earnings computed. */
  hasRate: boolean
  /** COMPLETED -- delivered work. */
  realized: EarningsRecord[]
  /** CONFIRMED -- accepted work that has not happened yet. */
  projected: EarningsRecord[]
  totalRealized: number
  totalProjected: number
  totalHours: number
}

function toRecord(appointment: Appointment, hourlyRate: number): EarningsRecord {
  const start = new Date(appointment.start_time).getTime()
  const end = new Date(appointment.end_time).getTime()
  const hours = Math.max(0, (end - start) / 3_600_000)
  return { appointment, hours, amount: hourlyRate * hours }
}

async function fetchLawyerEarnings(): Promise<LawyerEarnings> {
  let hourlyRate = 0
  try {
    const profile = await getMyLawyerProfile()
    hourlyRate = profile.hourly_rate ?? 0
  } catch {
    // No profile set up yet; report records at a 0 rate instead of failing the page.
  }

  const [confirmed, completed] = await Promise.all([
    listAppointments({ status: 'CONFIRMED', page_size: 100 }),
    listAppointments({ status: 'COMPLETED', page_size: 100 }),
  ])

  const byDateDesc = (a: Appointment, b: Appointment) =>
    new Date(b.start_time).getTime() - new Date(a.start_time).getTime()

  const projected = confirmed.items
    .filter((a) => a.status === 'CONFIRMED')
    .sort(byDateDesc)
    .map((a) => toRecord(a, hourlyRate))
  const realized = completed.items
    .filter((a) => a.status === 'COMPLETED')
    .sort(byDateDesc)
    .map((a) => toRecord(a, hourlyRate))

  const totalRealized = realized.reduce((sum, r) => sum + r.amount, 0)
  const totalProjected = projected.reduce((sum, r) => sum + r.amount, 0)

  return {
    hourlyRate,
    hasRate: hourlyRate > 0,
    realized,
    projected,
    totalRealized,
    totalProjected,
    totalHours: [...realized, ...projected].reduce((sum, r) => sum + r.hours, 0),
  }
}

/**
 * Earnings derived from the appointment workflow, split into what has been delivered
 * and what is still scheduled. Shared by the Earnings page and the lawyer dashboard so
 * both read the same `['lawyer-earnings']` cache entry.
 */
export function useLawyerEarnings() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['lawyer-earnings'],
    queryFn: fetchLawyerEarnings,
  })

  return {
    earnings: data ?? null,
    isLoading,
    isError,
    error,
    refetch,
  }
}
