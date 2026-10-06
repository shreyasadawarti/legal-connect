import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LawyerDashboard from '@/features/dashboard/LawyerDashboard'
import {
  confirmAppointment,
  listAppointments,
  rejectAppointment,
} from '@/services/appointmentService'
import { getMyLawyerProfile } from '@/services/lawyerService'
import { listNotifications } from '@/services/notificationService'
import { useAuthStore } from '@/stores/authStore'
import type { Appointment, AppointmentStatus } from '@/types/platform'

vi.mock('@/services/appointmentService', () => ({
  listAppointments: vi.fn(),
  confirmAppointment: vi.fn(),
  rejectAppointment: vi.fn(),
}))
vi.mock('@/services/lawyerService', () => ({
  getMyLawyerProfile: vi.fn(),
}))
vi.mock('@/services/notificationService', () => ({
  listNotifications: vi.fn(),
}))

const mockedList = vi.mocked(listAppointments)
const mockedConfirm = vi.mocked(confirmAppointment)
const mockedReject = vi.mocked(rejectAppointment)
const mockedProfile = vi.mocked(getMyLawyerProfile)
const mockedNotifications = vi.mocked(listNotifications)

const RATE = 100

const profile = {
  user_id: 'l'.repeat(24),
  name: 'Ananya Sharma',
  email: 'lawyer@example.com',
  bio: 'Experienced family lawyer',
  years_of_experience: 5,
  categories: ['family' as const],
  specializations: ['Divorce'],
  languages: ['English'],
  hourly_rate: RATE,
  city: 'Mumbai',
  availability: [],
  avg_rating: 4.5,
  rating_count: 12,
  verification_status: 'ACTIVE' as const,
  is_verified: true,
}

let seq = 0
function appt(status: AppointmentStatus, day: number): Appointment {
  seq += 1
  const d = String(day).padStart(2, '0')
  return {
    id: `a${seq}`.padEnd(24, '0'),
    lawyer_id: profile.user_id,
    lawyer_name: profile.name,
    client_id: `c${seq}`.padEnd(24, '0'),
    client_name: `Client ${seq}`,
    category: 'family',
    start_time: `2026-05-${d}T10:00:00Z`,
    end_time: `2026-05-${d}T11:00:00Z`,
    status,
  }
}

/** Answers both the dashboard's own query and the earnings hook's per-status queries. */
function routeAppointments(items: Appointment[]) {
  mockedList.mockImplementation(async (params) => {
    const filtered = params?.status ? items.filter((a) => a.status === params.status) : items
    return { items: filtered, total: filtered.length, page: 1, page_size: 100 }
  })
}

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LawyerDashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Stat tile labels are <p>; section headings with the same wording are <h2>. */
function statTile(label: string): HTMLElement {
  const el = screen.getAllByText(label).find((n) => n.tagName === 'P')
  if (!el) throw new Error(`No stat tile labelled "${label}"`)
  return el.closest('a')!
}

function section(heading: string): HTMLElement {
  return screen.getByRole('heading', { name: heading }).closest('section')!
}

function quickAction(title: string): HTMLElement {
  const el = screen.getAllByText(title).find((n) => n.tagName === 'H3')
  if (!el) throw new Error(`No quick action titled "${title}"`)
  return el
}

describe('LawyerDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    seq = 0
    useAuthStore.setState({
      user: {
        id: 'l'.repeat(24),
        name: 'Ananya Sharma',
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
    mockedProfile.mockResolvedValue({ ...profile })
    mockedNotifications.mockResolvedValue({
      items: [
        {
          id: 'n1',
          user_id: profile.user_id,
          type: 'APPOINTMENT',
          title: 'New booking request',
          message: 'Client 1 requested a family consultation.',
          is_read: false,
          created_at: '2026-05-01T00:00:00Z',
        },
      ],
      unread: 1,
      total: 1,
      page: 1,
      page_size: 20,
    })
  })

  it('shows a spinner and no error banner while data is still loading', () => {
    mockedList.mockReturnValue(new Promise(() => undefined))
    const { container } = renderDashboard()
    expect(container.querySelector('.animate-spin')).toBeTruthy()
    expect(screen.queryByText(/could not load dashboard data/i)).toBeNull()
  })

  it('surfaces an error banner instead of silent em dashes when appointments fail', async () => {
    mockedList.mockRejectedValue(new Error('network down'))
    renderDashboard()
    expect(await screen.findByText(/could not load dashboard data/i)).toBeTruthy()
    // The stat grid must not render misleading placeholder figures.
    expect(screen.queryByText('Pending requests')).toBeNull()
    expect(screen.queryByText('Quick actions')).toBeNull()
  })

  it('renders the six stat tiles', async () => {
    routeAppointments([])
    renderDashboard()
    await waitFor(() => expect(statTile('Pending requests')).toBeTruthy())
    for (const label of [
      'Earned',
      'Projected',
      'Pending requests',
      'Upcoming',
      'Completed',
      'Rating',
    ]) {
      expect(statTile(label)).toBeTruthy()
    }
  })

  it('splits earnings into earned and projected rather than one blended total', async () => {
    // Two completed hours at 100/hr = 200 earned, one confirmed hour = 100 projected.
    routeAppointments([
      appt('COMPLETED', 1),
      appt('COMPLETED', 2),
      appt('CONFIRMED', 3),
    ])
    renderDashboard()

    await waitFor(() => expect(statTile('Earned').textContent).toContain('₹200'))
    expect(statTile('Earned').textContent).toContain('2 completed')
    expect(statTile('Projected').textContent).toContain('₹100')
    expect(statTile('Projected').textContent).toContain('1 confirmed')
  })

  it('does not count a pending appointment as projected earnings', async () => {
    routeAppointments([appt('PENDING', 1)])
    renderDashboard()
    await waitFor(() => expect(statTile('Projected').textContent).toContain('₹0'))
    expect(statTile('Projected').textContent).toContain('0 confirmed')
    expect(statTile('Pending requests').textContent).toContain('1')
  })

  it('does not count a rejected appointment as earnings at all', async () => {
    routeAppointments([appt('REJECTED', 1), appt('CANCELLED', 2)])
    renderDashboard()
    await waitFor(() => expect(statTile('Earned').textContent).toContain('₹0'))
    expect(statTile('Projected').textContent).toContain('₹0')
  })

  it('offers accept and decline on each pending request', async () => {
    routeAppointments([appt('PENDING', 1), appt('PENDING', 2)])
    renderDashboard()

    await waitFor(() => expect(screen.getByRole('heading', { name: /pending requests/i })).toBeTruthy())
    expect(screen.getAllByRole('button', { name: /accept/i })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /decline/i })).toHaveLength(2)
  })

  it('accepting a pending request calls confirmAppointment', async () => {
    const target = appt('PENDING', 1)
    routeAppointments([target])
    mockedConfirm.mockResolvedValue({ ...target, status: 'CONFIRMED' })

    renderDashboard()
    await waitFor(() => expect(screen.getByRole('button', { name: /accept/i })).toBeTruthy())
    await userEvent.click(screen.getByRole('button', { name: /accept/i }))

    await waitFor(() => expect(mockedConfirm).toHaveBeenCalledWith(target.id))
  })

  it('declining a pending request calls rejectAppointment', async () => {
    const target = appt('PENDING', 1)
    routeAppointments([target])
    mockedReject.mockResolvedValue({ ...target, status: 'REJECTED' })

    renderDashboard()
    await waitFor(() => expect(screen.getByRole('button', { name: /decline/i })).toBeTruthy())
    await userEvent.click(screen.getByRole('button', { name: /decline/i }))

    await waitFor(() => expect(mockedReject).toHaveBeenCalledWith(target.id))
  })

  it('shows no accept controls when nothing is pending', async () => {
    routeAppointments([appt('CONFIRMED', 1)])
    renderDashboard()
    await waitFor(() => expect(statTile('Upcoming').textContent).toContain('1'))
    expect(screen.queryByRole('button', { name: /accept/i })).toBeNull()
    expect(section('Pending requests').textContent).toContain(
      'No requests waiting on you.',
    )
  })

  it('sorts upcoming consultations by start time', async () => {
    routeAppointments([appt('CONFIRMED', 9), appt('CONFIRMED', 4)])
    renderDashboard()

    await waitFor(() =>
      expect(section('Upcoming consultations')).toBeTruthy(),
    )
    const text = section('Upcoming consultations').textContent!
    expect(text.indexOf('Client 2')).toBeLessThan(text.indexOf('Client 1'))
  })

  it('lists recently completed consultations', async () => {
    routeAppointments([appt('COMPLETED', 1)])
    renderDashboard()
    await waitFor(() => expect(section('Recently completed')).toBeTruthy())
    expect(section('Recently completed').textContent).toContain('Client 1')
  })

  it('shows recent activity from notifications', async () => {
    routeAppointments([])
    renderDashboard()
    await waitFor(() => expect(section('Recent activity')).toBeTruthy())
    expect(section('Recent activity').textContent).toContain('New booking request')
  })

  it('prompts to complete the profile when the bio is missing', async () => {
    mockedProfile.mockResolvedValue({ ...profile, bio: '' })
    routeAppointments([])
    renderDashboard()
    expect(await screen.findByText(/complete your lawyer profile/i)).toBeTruthy()
  })

  it('hides the profile-completion prompt once the bio is filled in', async () => {
    routeAppointments([])
    renderDashboard()
    await waitFor(() => expect(statTile('Rating')).toBeTruthy())
    expect(screen.queryByText(/complete your lawyer profile/i)).toBeNull()
  })

  it('surfaces the admin rejection reason', async () => {
    mockedProfile.mockResolvedValue({
      ...profile,
      verification_status: 'REJECTED',
      rejection_reason: 'Bar council licence could not be verified.',
    })
    routeAppointments([])
    renderDashboard()
    expect(
      await screen.findByText('Bar council licence could not be verified.'),
    ).toBeTruthy()
  })

  it('reports a missing hourly rate instead of implying zero earnings', async () => {
    mockedProfile.mockResolvedValue({ ...profile, hourly_rate: 0 })
    routeAppointments([])
    renderDashboard()
    await waitFor(() => expect(section('Profile & verification')).toBeTruthy())
    expect(section('Profile & verification').textContent).toContain('Not set')
  })

  it('offers all six quick action links', async () => {
    routeAppointments([])
    renderDashboard()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Quick actions' })).toBeTruthy())
    for (const title of [
      'Appointments',
      'Availability',
      'Earnings',
      'Messages',
      'Documents',
      'Profile',
    ]) {
      expect(quickAction(title).closest('a')).toBeTruthy()
    }
  })

  it('links every quick action to a real lawyer route', async () => {
    routeAppointments([])
    renderDashboard()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Quick actions' })).toBeTruthy())
    const hrefs = [...document.querySelectorAll('a')].map((a) => a.getAttribute('href'))
    for (const route of [
      '/lawyer/appointments',
      '/lawyer/availability',
      '/lawyer/earnings',
      '/lawyer/chat',
      '/lawyer/documents',
      '/lawyer/profile',
    ]) {
      expect(hrefs).toContain(route)
    }
  })
})
