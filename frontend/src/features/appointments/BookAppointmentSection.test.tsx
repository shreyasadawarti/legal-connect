import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import BookAppointmentSection from './BookAppointmentSection'
import { bookAppointment } from '@/services/appointmentService'
import type { LawyerProfile } from '@/types/platform'

vi.mock('@/services/appointmentService', () => ({
  bookAppointment: vi.fn().mockResolvedValue({}),
}))

const mockedBook = vi.mocked(bookAppointment)

const lawyer: LawyerProfile = {
  user_id: 'l'.repeat(24),
  name: 'Ananya Sharma',
  email: 'ananya@example.com',
  bio: '',
  years_of_experience: 5,
  categories: ['family'],
  specializations: [],
  languages: ['English'],
  hourly_rate: 1000,
  availability: [],
  avg_rating: 0,
  rating_count: 0,
  verification_status: 'ACTIVE',
  is_verified: true,
}

function tomorrowISO() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function setDate(value: string) {
  fireEvent.change(screen.getByLabelText('Date'), { target: { value } })
}

async function pickTime() {
  setDate(tomorrowISO())
  await userEvent.selectOptions(screen.getByLabelText('Hour'), '10')
  await userEvent.selectOptions(screen.getByLabelText('Minute'), '15')
  await userEvent.selectOptions(screen.getByLabelText('AM or PM'), 'PM')
}

function renderSection() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <BookAppointmentSection lawyer={lawyer} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  mockedBook.mockClear()
})

describe('BookAppointmentSection time picker', () => {
  it('keeps the selected hour, minute and AM/PM and commits them via Done', async () => {
    renderSection()
    await userEvent.click(screen.getByRole('button', { name: 'Select date & time' }))
    await pickTime()
    await userEvent.click(screen.getByRole('button', { name: 'Done' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /10:15/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Request appointment' })).toBeEnabled()
  })

  it('shows an error when Done is clicked before AM/PM is chosen', async () => {
    renderSection()
    await userEvent.click(screen.getByRole('button', { name: 'Select date & time' }))
    setDate(tomorrowISO())
    await userEvent.selectOptions(screen.getByLabelText('Hour'), '10')
    await userEvent.selectOptions(screen.getByLabelText('Minute'), '15')
    await userEvent.click(screen.getByRole('button', { name: 'Done' }))

    expect(screen.getByText('Please select a date, time and AM/PM.')).toBeInTheDocument()
  })

  it('still submits the picked time to bookAppointment', async () => {
    renderSection()
    await userEvent.click(screen.getByRole('button', { name: 'Select date & time' }))
    await pickTime()
    await userEvent.click(screen.getByRole('button', { name: 'Done' }))
    await userEvent.click(screen.getByRole('button', { name: 'Request appointment' }))

    const localStart = new Date(`${tomorrowISO()}T22:15`)
    expect(mockedBook).toHaveBeenCalledWith(
      expect.objectContaining({
        lawyer_id: lawyer.user_id,
        start_time: localStart.toISOString(),
        end_time: new Date(localStart.getTime() + 60 * 60000).toISOString(),
      }),
    )
  })
})