import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminDashboard from '@/features/dashboard/AdminDashboard'
import { adminAnalytics, adminDashboard } from '@/services/adminService'
import type { AdminAnalytics, AdminDashboardStats } from '@/types/platform'

vi.mock('@/services/adminService', () => ({
  adminAnalytics: vi.fn(),
  adminDashboard: vi.fn(),
}))

// recharts' ResponsiveContainer observes its box; jsdom has no ResizeObserver.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeAll(() => {
  ;(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub
})

const mockedDashboard = vi.mocked(adminDashboard)
const mockedAnalytics = vi.mocked(adminAnalytics)

const stats: AdminDashboardStats = {
  total_users: 10,
  total_lawyers: 6,
  total_appointments: 17,
  pending_verifications: 1,
  open_complaints: 2,
  total_revenue: 238000,
}

const analytics: AdminAnalytics = {
  users_by_role: { user: 10, lawyer: 6, admin: 1 },
  appointments_by_status: { COMPLETED: 11, CONFIRMED: 3, PENDING: 3 },
  lawyers_by_status: { ACTIVE: 6 },
  complaints_by_status: {},
  appointments_by_month: [],
  top_categories: [],
  top_lawyers: [],
  revenue_by_source: { registration: 100000, commission: 138000 },
}

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminDashboard', () => {
  beforeEach(() => {
    mockedDashboard.mockResolvedValue(stats)
    mockedAnalytics.mockResolvedValue(analytics)
  })

  it('shows total revenue in Indian Rupee format', async () => {
    renderDashboard()
    expect(await screen.findByText('₹2,38,000')).toBeTruthy()
  })

  it('keeps the revenue label alongside the amount', async () => {
    renderDashboard()
    await waitFor(() => {
      const label = screen.getByText('Revenue')
      expect(label).toBeTruthy()
      expect(label.parentElement?.textContent).toContain('₹2,38,000')
    })
  })
})