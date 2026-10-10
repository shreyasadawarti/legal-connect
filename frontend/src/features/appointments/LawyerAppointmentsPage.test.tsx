import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LawyerAppointmentsPage from '@/features/appointments/LawyerAppointmentsPage'
import { listAppointments } from '@/services/appointmentService'
import { createConversation } from '@/services/chatService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment } from '@/types/platform'

vi.mock('@/services/appointmentService', () => ({
  listAppointments: vi.fn(),
  confirmAppointment: vi.fn(),
  rejectAppointment: vi.fn(),
  completeAppointment: vi.fn(),
}))
vi.mock('@/services/chatService', () => ({
  createConversation: vi.fn(),
}))

const mockedList = vi.mocked(listAppointments)
const mockedCreateConversation = vi.mocked(createConversation)

const LAWYER_ID = 'l'.repeat(24)
const CLIENT_ID = 'c'.repeat(24)
const APPOINTMENT_ID = 'a'.repeat(24)

function appt(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: APPOINTMENT_ID,
    lawyer_id: LAWYER_ID,
    lawyer_name: 'Test Lawyer',
    client_id: CLIENT_ID,
    client_name: 'Test User',
    category: 'family',
    start_time: '2026-05-01T10:00:00Z',
    end_time: '2026-05-01T11:00:00Z',
    status: 'CONFIRMED',
    ...overrides,
  }
}

function renderWithChatRoute() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <MemoryRouter initialEntries={['/lawyer/appointments']}>
      <Routes>
        <Route
          path="/lawyer/appointments"
          element={
            <QueryClientProvider client={queryClient}>
              <LawyerAppointmentsPage />
            </QueryClientProvider>
          }
        />
        <Route path="/lawyer/chat" element={<div>Lawyer Chat Landed</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LawyerAppointmentsPage video-call link sharing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: LAWYER_ID,
        name: 'Test Lawyer',
        email: 'lawyer@example.com',
        role: 'lawyer',
        status: 'ACTIVE',
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
    })
    mockedList.mockResolvedValue({ items: [appt()], total: 1, page: 1, page_size: 20 })
    mockedCreateConversation.mockResolvedValue({
      id: 'z'.repeat(24),
      type: 'direct',
      peers: [],
      last_message: '',
      unread_count: 0,
    } as never)
  })

  it('sends the video-call link to the citizen through chat and opens the lawyer chat page', async () => {
    renderWithChatRoute()
    await userEvent.click(await screen.findByRole('button', { name: /send link via chat/i }))

    await waitFor(() =>
      expect(mockedCreateConversation).toHaveBeenCalledWith(
        CLIENT_ID,
        `${window.location.origin}/video-call/${APPOINTMENT_ID}`,
      ),
    )
    expect(await screen.findByText('Lawyer Chat Landed')).toBeTruthy()
  })
})
