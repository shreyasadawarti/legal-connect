import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReportLawyerSection from '@/features/lawyers/ReportLawyerSection'
import { listAppointments } from '@/services/appointmentService'
import { createComplaint } from '@/services/socialService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment } from '@/types/platform'

vi.mock('@/services/appointmentService', () => ({
  listAppointments: vi.fn(),
}))
vi.mock('@/services/socialService', () => ({
  createComplaint: vi.fn(),
}))

const mockedList = vi.mocked(listAppointments)
const mockedCreate = vi.mocked(createComplaint)

const LAWYER_ID = 'l'.repeat(24)
const OTHER_LAWYER_ID = 'o'.repeat(24)

function appt(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: 'a'.repeat(24),
    lawyer_id: LAWYER_ID,
    lawyer_name: 'Ananya Sharma',
    client_id: 'c'.repeat(24),
    client_name: 'Test User',
    category: 'family',
    start_time: '2026-05-01T10:00:00Z',
    end_time: '2026-05-01T11:00:00Z',
    status: 'COMPLETED',
    ...overrides,
  }
}

function renderSection() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReportLawyerSection lawyerUserId={LAWYER_ID} />
    </QueryClientProvider>,
  )
}

const REPORT = /report this lawyer/i

describe('ReportLawyerSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: 'c'.repeat(24),
        name: 'Test User',
        email: 'user@example.com',
        role: 'user',
        status: 'ACTIVE',
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('hides the complaint option for a lawyer the citizen has never booked', async () => {
    mockedList.mockResolvedValue({
      items: [appt({ id: 'b'.repeat(24), lawyer_id: OTHER_LAWYER_ID })],
      total: 1,
      page: 1,
      page_size: 100,
    })
    renderSection()
    await waitFor(() => expect(mockedList).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: REPORT })).toBeNull()
    expect(screen.queryByText(REPORT)).toBeNull()
  })

  it('hides the complaint option when the citizen has no appointments at all', async () => {
    mockedList.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    renderSection()
    await waitFor(() => expect(mockedList).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: REPORT })).toBeNull()
  })

  it('offers the complaint option once the citizen has an appointment with that lawyer', async () => {
    mockedList.mockResolvedValue({
      items: [appt()],
      total: 1,
      page: 1,
      page_size: 100,
    })
    renderSection()
    expect(await screen.findByRole('button', { name: REPORT })).toBeTruthy()
  })

  it('matches an appointment on any status, including a pending one', async () => {
    mockedList.mockResolvedValue({
      items: [appt({ status: 'PENDING' })],
      total: 1,
      page: 1,
      page_size: 100,
    })
    renderSection()
    expect(await screen.findByRole('button', { name: REPORT })).toBeTruthy()
  })

  it('submits the complaint against the most recent appointment', async () => {
    const older = appt({ id: 'd'.repeat(24), start_time: '2026-01-01T10:00:00Z' })
    const newer = appt({ id: 'e'.repeat(24), start_time: '2026-06-01T10:00:00Z' })
    mockedList.mockResolvedValue({ items: [older, newer], total: 2, page: 1, page_size: 100 })
    mockedCreate.mockResolvedValue({ id: 'x', status: 'OPEN' } as never)

    renderSection()
    await userEvent.click(await screen.findByRole('button', { name: REPORT }))
    await userEvent.type(screen.getByLabelText(/subject/i), 'Missed appointment')
    await userEvent.type(screen.getByLabelText(/what happened/i), 'The lawyer never showed up.')
    await userEvent.click(screen.getByRole('button', { name: /submit complaint/i }))

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledTimes(1))
    expect(mockedCreate).toHaveBeenCalledWith({
      subject: 'Missed appointment',
      description: 'The lawyer never showed up.',
      related_appointment_id: newer.id,
    })
  })

  it('shows a confirmation and clears the form after a successful submission', async () => {
    mockedList.mockResolvedValue({ items: [appt()], total: 1, page: 1, page_size: 100 })
    mockedCreate.mockResolvedValue({ id: 'x', status: 'OPEN' } as never)

    renderSection()
    await userEvent.click(await screen.findByRole('button', { name: REPORT }))
    await userEvent.type(screen.getByLabelText(/subject/i), 'Unprofessional')
    await userEvent.type(screen.getByLabelText(/what happened/i), 'Rude behaviour.')
    await userEvent.click(screen.getByRole('button', { name: /submit complaint/i }))

    expect(await screen.findByText(/complaint submitted/i)).toBeTruthy()
  })

  it('never calls the appointments API for a lawyer', async () => {
    useAuthStore.setState((s) => ({ ...s, user: { ...s.user!, role: 'lawyer' } }))
    mockedList.mockResolvedValue({ items: [appt()], total: 1, page: 1, page_size: 100 })
    renderSection()
    await waitFor(() => expect(screen.queryByRole('button', { name: REPORT })).toBeNull())
    expect(mockedList).not.toHaveBeenCalled()
  })
})
