import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar, Loader2 } from 'lucide-react'
import { useState } from 'react'

import { bookAppointment } from '@/services/appointmentService'
import type { LawyerProfile } from '@/types/platform'

export default function BookAppointmentSection({ lawyer }: { lawyer: LawyerProfile }) {
  const queryClient = useQueryClient()
  const [start, setStart] = useState('')
  const [durationMin, setDurationMin] = useState(60)
  const [description, setDescription] = useState('')
  const [success, setSuccess] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [pickDate, setPickDate] = useState('')
  const [pickHour12, setPickHour12] = useState('')
  const [pickMinute, setPickMinute] = useState('')
  const [pickMeridiem, setPickMeridiem] = useState('')
  const [pickerError, setPickerError] = useState('')

  const now = new Date()
  const todayISO = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const isPastStart = Boolean(start) && new Date(start).getTime() < Date.now()

  const openPicker = () => {
    if (start) {
      const [d, t] = start.split('T')
      setPickDate(d)
      const [h24, m] = t.split(':')
      const h24n = Number(h24)
      setPickHour12(String(h24n % 12 || 12))
      setPickMinute(m)
      setPickMeridiem(h24n < 12 ? 'AM' : 'PM')
    } else {
      setPickDate('')
      setPickHour12('')
      setPickMinute('')
      setPickMeridiem('')
    }
    setPickerError('')
    setPickerOpen(true)
  }

  const confirmPicker = () => {
    if (!pickDate || !pickHour12 || !pickMinute || !pickMeridiem) {
      setPickerError('Please select a date, time and AM/PM.')
      return
    }
    const h24 = (Number(pickHour12) % 12) + (pickMeridiem === 'PM' ? 12 : 0)
    const pickTime = `${String(h24).padStart(2, '0')}:${pickMinute}`
    if (new Date(`${pickDate}T${pickTime}`).getTime() < Date.now()) {
      setPickerError('Please select a current or future time.')
      return
    }
    setStart(`${pickDate}T${pickTime}`)
    setPickerError('')
    setPickerOpen(false)
  }

  const startDisplay = start
    ? new Date(start).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : ''

  const pickHour24 =
    pickHour12 && pickMeridiem
      ? (Number(pickHour12) % 12) + (pickMeridiem === 'PM' ? 12 : 0)
      : -1
  const dateIsToday = pickDate === todayISO

  const hourOptionDisabled = (hour12: string, meridiem: string) => {
    if (!dateIsToday || !meridiem) return false
    const h24 = (Number(hour12) % 12) + (meridiem === 'PM' ? 12 : 0)
    return h24 < now.getHours()
  }

  const meridiemOptionDisabled = (meridiem: string) => {
    if (!dateIsToday) return false
    return meridiem === 'AM' && now.getHours() >= 12
  }

  const minuteOptionDisabled = (minute: string) => {
    if (!dateIsToday || pickHour24 < 0) return false
    if (pickHour24 !== now.getHours()) return pickHour24 < now.getHours()
    return Number(minute) < now.getMinutes()
  }

  const mutation = useMutation({
    mutationFn: () => {
      const startDate = new Date(start)
      const endDate = new Date(startDate.getTime() + durationMin * 60000)
      return bookAppointment({
        lawyer_id: lawyer.user_id,
        category: lawyer.categories[0] ?? 'other',
        start_time: startDate.toISOString(),
        end_time: endDate.toISOString(),
        description: description || undefined,
      })
    },
    onSuccess: () => {
      setSuccess(true)
      setStart('')
      setDescription('')
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
    },
  })

  const errorMsg = (mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
      <h3 className="flex items-center gap-2 text-lg font-semibold">
        <Calendar className="h-5 w-5 text-brand-600" /> Book a consultation
      </h3>
      {success && (
        <p className="mt-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
          Appointment requested! The lawyer will confirm your booking.
        </p>
      )}
      {errorMsg && (
        <p className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {errorMsg}
        </p>
      )}
      {!success && (
        <form
          className="mt-4 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <div>
            <label className="mb-1 block text-sm font-medium">Start date &amp; time</label>
            <button
              type="button"
              onClick={openPicker}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-left text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            >
              {startDisplay || 'Select date & time'}
            </button>
            {isPastStart && (
              <p className="mt-1 text-xs text-amber-600">
                The selected time is in the past. Please pick a new slot.
              </p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Duration</label>
            <select
              value={durationMin}
              onChange={(e) => setDurationMin(Number(e.target.value))}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            >
              <option value={30}>30 minutes</option>
              <option value={60}>1 hour</option>
              <option value={90}>1.5 hours</option>
              <option value={120}>2 hours</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Describe your issue (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled={!start || isPastStart || mutation.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Request appointment
          </button>
        </form>
      )}

      {pickerOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4"
        >
          <div className="my-auto w-full max-w-sm rounded-2xl border border-surface-200 bg-white p-5 shadow-xl dark:border-surface-700 dark:bg-surface-800">
            <h4 className="font-semibold">Pick a date &amp; time</h4>
            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium">Date</label>
                <input
                  type="date"
                  aria-label="Date"
                  value={pickDate}
                  min={todayISO}
                  onChange={(e) => {
                    setPickDate(e.target.value)
                    setPickerError('')
                  }}
                  className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Time</label>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label="Hour"
                    value={pickHour12}
                    onChange={(e) => {
                      setPickHour12(e.target.value)
                      setPickerError('')
                    }}
                    className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                  >
                    <option value="">HH</option>
                    {Array.from({ length: 12 }, (_, i) => String(i + 1)).map((h) => (
                      <option key={h} value={h} disabled={hourOptionDisabled(h, pickMeridiem)}>
                        {h}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Minute"
                    value={pickMinute}
                    onChange={(e) => {
                      setPickMinute(e.target.value)
                      setPickerError('')
                    }}
                    className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                  >
                    <option value="">MM</option>
                    {Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0')).map((m) => (
                      <option key={m} value={m} disabled={minuteOptionDisabled(m)}>
                        {m}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="AM or PM"
                    value={pickMeridiem}
                    onChange={(e) => {
                      setPickMeridiem(e.target.value)
                      setPickerError('')
                    }}
                    className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                  >
                    <option value="">AM/PM</option>
                    <option value="AM" disabled={meridiemOptionDisabled('AM')}>
                      AM
                    </option>
                    <option value="PM" disabled={meridiemOptionDisabled('PM')}>
                      PM
                    </option>
                  </select>
                </div>
              </div>
              {pickerError && <p className="text-xs text-red-600">{pickerError}</p>}
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setPickerOpen(false)
                    setPickerError('')
                  }}
                  className="rounded-lg border border-surface-300 px-4 py-2 text-sm hover:bg-surface-100 dark:border-surface-600 dark:hover:bg-surface-700"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmPicker}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
