import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminComplaintsPage from '@/features/admin/AdminComplaintsPage'
import { adminListComplaints, adminRespondComplaint } from '@/services/adminService'
import type { AdminComplaintItem } from '@/types/platform'

vi.mock('@/services/adminService', () => ({
  adminListComplaints: vi.fn(),
  adminRespondComplaint: vi.fn(),
}))

const mockedList = vi.mocked(adminListComplaints)
const mockedRespond = vi.mocked(adminRespondComplaint)

function complaint(overrides: Partial<AdminComplaintItem> = {}): AdminComplaintItem {
  return {
    id: 'k'.repeat(24),
    user_id: 'r'.repeat(24),
    user_name: 'Reporter',
    user_email: 'reporter@example.com',
    target_user_id: 't'.repeat(24),
    target_user_name: 'Reported User',
    target_user_email: 'reported@example.com',
    category: 'harassment',
    subject: 'Rude behaviour',
    description: 'The lawyer was rude during the call.',
    status: 'IN_PROGRESS',
    reporter_response: 'We are looking into your report.',
    reporter_responded_at: '2026-05-01T10:00:00Z',
    reported_response: 'Please share your side of the story.',
    reported_responded_at: '2026-05-01T10:05:00Z',
    created_at: '2026-05-01T09:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AdminComplaintsPage />
    </QueryClientProvider>,
  )
}

describe('AdminComplaintsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows both stored responses with the party each is addressed to', async () => {
    mockedList.mockResolvedValue({
      items: [complaint()],
      total: 1,
      page: 1,
      page_size: 50,
    })

    renderPage()

    expect(await screen.findByText('Rude behaviour')).toBeTruthy()
    expect(screen.getByText('We are looking into your report.')).toBeTruthy()
    expect(screen.getByText('Please share your side of the story.')).toBeTruthy()
    expect(screen.getByText(/to reporter \(Reporter\)/i)).toBeTruthy()
    expect(screen.getByText(/to reported user/i)).toBeTruthy()
  })

  it('prefills and submits a separate response for each party', async () => {
    mockedList.mockResolvedValue({
      items: [complaint()],
      total: 1,
      page: 1,
      page_size: 50,
    })
    mockedRespond.mockResolvedValue(complaint())

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /respond/i }))

    const reporterBox = screen.getByPlaceholderText(
      /message the person who filed the complaint/i,
    ) as HTMLTextAreaElement
    const reportedBox = screen.getByPlaceholderText(
      /message the person who was reported/i,
    ) as HTMLTextAreaElement
    expect(reporterBox.value).toBe('We are looking into your report.')
    expect(reportedBox.value).toBe('Please share your side of the story.')

    await userEvent.clear(reporterBox)
    await userEvent.type(reporterBox, 'Updated reply for the reporter.')
    await userEvent.click(screen.getByRole('button', { name: /save response/i }))

    await waitFor(() => expect(mockedRespond).toHaveBeenCalledTimes(1))
    expect(mockedRespond).toHaveBeenCalledWith('k'.repeat(24), {
      status: 'IN_PROGRESS',
      reporterResponse: 'Updated reply for the reporter.',
      reportedResponse: 'Please share your side of the story.',
    })
  })

  it('still offers respond after the complaint is resolved', async () => {
    mockedList.mockResolvedValue({
      items: [complaint({ status: 'RESOLVED' })],
      total: 1,
      page: 1,
      page_size: 50,
    })

    renderPage()

    expect(await screen.findByRole('button', { name: /respond/i })).toBeTruthy()
  })

  it('omits the reported-party box when the complaint has no target', async () => {
    mockedList.mockResolvedValue({
      items: [
        complaint({
          target_user_id: undefined,
          target_user_name: undefined,
          target_user_email: undefined,
          reported_response: undefined,
          reported_responded_at: undefined,
        }),
      ],
      total: 1,
      page: 1,
      page_size: 50,
    })

    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /respond/i }))

    expect(screen.queryByPlaceholderText(/message the person who was reported/i)).toBeNull()
    expect(
      screen.getByPlaceholderText(/message the person who filed the complaint/i),
    ).toBeTruthy()
  })
})
