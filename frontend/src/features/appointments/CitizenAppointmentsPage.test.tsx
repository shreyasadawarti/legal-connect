import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CitizenAppointmentsPage from '@/features/appointments/CitizenAppointmentsPage'
import { openRazorpayCheckout } from '@/lib/razorpay'
import { listAppointments } from '@/services/appointmentService'
import { createConversation } from '@/services/chatService'
import { createPaymentOrder, getAppointmentPayment, verifyPayment } from '@/services/paymentService'
import { submitReview } from '@/services/socialService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment } from '@/types/platform'

vi.mock('@/services/appointmentService', () => ({
  listAppointments: vi.fn(),
  cancelAppointment: vi.fn(),
}))
vi.mock('@/services/chatService', () => ({
  createConversation: vi.fn(),
}))
vi.mock('@/services/socialService', () => ({
  submitReview: vi.fn(),
}))
vi.mock('@/services/paymentService', () => ({
  getAppointmentPayment: vi.fn(),
  createPaymentOrder: vi.fn(),
  verifyPayment: vi.fn(),
}))
vi.mock('@/lib/razorpay', () => ({
  openRazorpayCheckout: vi.fn(),
}))

const mockedList = vi.mocked(listAppointments)
const mockedCreateConversation = vi.mocked(createConversation)
const mockedSubmit = vi.mocked(submitReview)
const mockedGetPayment = vi.mocked(getAppointmentPayment)
const mockedCreateOrder = vi.mocked(createPaymentOrder)
const mockedVerify = vi.mocked(verifyPayment)
const mockedCheckout = vi.mocked(openRazorpayCheckout)

const USER_ID = 'c'.repeat(24)
const LAWYER_ID = 'l'.repeat(24)

function appt(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: 'a'.repeat(24),
    lawyer_id: LAWYER_ID,
    lawyer_name: 'Ananya Sharma',
    client_id: USER_ID,
    client_name: 'Test User',
    category: 'family',
    start_time: '2026-05-01T10:00:00Z',
    end_time: '2026-05-01T11:00:00Z',
    status: 'COMPLETED',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <CitizenAppointmentsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('CitizenAppointmentsPage review status', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: USER_ID,
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
    mockedList.mockResolvedValue({ items: [appt()], total: 1, page: 1, page_size: 20 })
    mockedGetPayment.mockResolvedValue(null)
  })

  it('offers "Leave a review" on a completed appointment not yet reviewed', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: /leave a review/i })).toBeTruthy()
    expect(screen.queryByText('Review Done')).toBeNull()
  })

  it('shows "Review Done" when the appointment is already reviewed', async () => {
    mockedList.mockResolvedValue({
      items: [appt({ reviewed: true })],
      total: 1,
      page: 1,
      page_size: 20,
    })
    renderPage()
    expect(await screen.findByText('Review Done')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /leave a review/i })).toBeNull()
  })

  it('tracks review state per appointment, not per lawyer', async () => {
    mockedList.mockResolvedValue({
      items: [
        appt({ id: 'a'.repeat(24), reviewed: true }),
        appt({ id: 'b'.repeat(24), reviewed: false }),
      ],
      total: 2,
      page: 1,
      page_size: 20,
    })
    renderPage()
    expect(await screen.findByText('Review Done')).toBeTruthy()
    expect(screen.getAllByRole('button', { name: /leave a review/i })).toHaveLength(1)
  })

  it('never offers a review on a non-completed appointment', async () => {
    mockedList.mockResolvedValue({
      items: [appt({ status: 'CONFIRMED' })],
      total: 1,
      page: 1,
      page_size: 20,
    })
    renderPage()
    await waitFor(() => expect(mockedList).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: /leave a review/i })).toBeNull()
  })

  it('requires a written review before the submit button is enabled', async () => {
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /leave a review/i }))
    const submit = screen.getByRole('button', { name: /submit review/i }) as HTMLButtonElement
    expect(submit.disabled).toBe(true)
    await userEvent.type(
      screen.getByPlaceholderText(/share your experience/i),
      'Very helpful',
    )
    expect(submit.disabled).toBe(false)
  })

  it('flips to "Review Done" immediately after a successful submission', async () => {
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /leave a review/i }))
    await userEvent.type(
      screen.getByPlaceholderText(/share your experience/i),
      'Very helpful',
    )
    mockedSubmit.mockResolvedValue({ data: {} } as never)

    await userEvent.click(screen.getByRole('button', { name: /submit review/i }))

    expect(await screen.findByText('Review Done')).toBeTruthy()
    expect(mockedSubmit).toHaveBeenCalledWith(LAWYER_ID, 5, 'Very helpful', appt().id)
    expect(screen.queryByRole('button', { name: /leave a review/i })).toBeNull()
  })

  it('collapses to "Review Done" on a 409 duplicate without an error message', async () => {
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /leave a review/i }))
    await userEvent.type(screen.getByPlaceholderText(/share your experience/i), 'Good')
    mockedSubmit.mockRejectedValue({ response: { status: 409 } })

    await userEvent.click(screen.getByRole('button', { name: /submit review/i }))

    expect(await screen.findByText('Review Done')).toBeTruthy()
    expect(screen.queryByText(/could not submit your review/i)).toBeNull()
  })

  it('shows an error when the submission fails for another reason', async () => {
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /leave a review/i }))
    await userEvent.type(screen.getByPlaceholderText(/share your experience/i), 'Good')
    mockedSubmit.mockRejectedValue({ response: { status: 500 } })

    await userEvent.click(screen.getByRole('button', { name: /submit review/i }))

    expect(await screen.findByText(/could not submit your review/i)).toBeTruthy()
    expect(screen.queryByText('Review Done')).toBeNull()
  })
})

describe('CitizenAppointmentsPage video-call link sharing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: USER_ID,
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
    mockedList.mockResolvedValue({
      items: [appt({ status: 'CONFIRMED' })],
      total: 1,
      page: 1,
      page_size: 20,
    })
    mockedCreateConversation.mockResolvedValue({
      id: 'z'.repeat(24),
      type: 'direct',
      peers: [],
      last_message: '',
      unread_count: 0,
    } as never)
    mockedGetPayment.mockResolvedValue(null)
  })

  function renderWithChatRoute() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    return render(
      <MemoryRouter initialEntries={['/appointments']}>
        <Routes>
          <Route
            path="/appointments"
            element={
              <QueryClientProvider client={queryClient}>
                <CitizenAppointmentsPage />
              </QueryClientProvider>
            }
          />
          <Route path="/chat" element={<div>Chat Landed</div>} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it('sends the video-call link to the lawyer through chat and opens the chat page', async () => {
    renderWithChatRoute()
    await userEvent.click(
      await screen.findByRole('button', { name: /send link via chat/i }),
    )

    await waitFor(() =>
      expect(mockedCreateConversation).toHaveBeenCalledWith(
        LAWYER_ID,
        `${window.location.origin}/video-call/${appt().id}`,
      ),
    )
    expect(await screen.findByText('Chat Landed')).toBeTruthy()
  })
})

describe('CitizenAppointmentsPage payments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: USER_ID,
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
    mockedList.mockResolvedValue({
      items: [appt({ status: 'CONFIRMED' })],
      total: 1,
      page: 1,
      page_size: 20,
    })
    mockedGetPayment.mockResolvedValue(null)
  })

  it('shows a pay button for a confirmed unpaid appointment', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: /pay consultation fee/i })).toBeTruthy()
  })

  it('shows a Paid badge and no pay button once paid', async () => {
    mockedGetPayment.mockResolvedValue({
      id: 'p'.repeat(24),
      appointment_id: appt().id,
      payee_id: USER_ID,
      amount: 100,
      status: 'PAID',
      reference: 'LC-TEST',
    })
    renderPage()
    expect(await screen.findByText('Paid')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /pay consultation fee/i })).toBeNull()
  })

  it('opens checkout and verifies the captured payment', async () => {
    mockedCreateOrder.mockResolvedValue({
      payment_id: 'p'.repeat(24),
      appointment_id: appt().id,
      order_id: 'order_1',
      amount: 100,
      amount_paise: 10000,
      currency: 'INR',
      key_id: 'rzp_test',
      reference: 'LC-TEST',
      description: 'Legal consultation',
    })
    mockedCheckout.mockResolvedValue({
      razorpay_payment_id: 'pay_1',
      razorpay_order_id: 'order_1',
      razorpay_signature: 'sig',
    })
    mockedVerify.mockResolvedValue({} as never)

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /pay consultation fee/i }))

    await waitFor(() => expect(mockedCreateOrder).toHaveBeenCalledWith(appt().id))
    await waitFor(() =>
      expect(mockedVerify).toHaveBeenCalledWith({
        payment_id: 'p'.repeat(24),
        razorpay_order_id: 'order_1',
        razorpay_payment_id: 'pay_1',
        razorpay_signature: 'sig',
      }),
    )
  })

  it('surfaces the gateway-not-configured message', async () => {
    mockedCreateOrder.mockRejectedValue({
      response: { data: { detail: 'Payment gateway is not configured.' } },
    })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /pay consultation fee/i }))
    expect(await screen.findByText(/payment gateway is not configured/i)).toBeTruthy()
  })
})
