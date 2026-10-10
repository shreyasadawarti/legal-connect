import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ComplaintsPage from '@/features/complaints/ComplaintsPage'
import {
  createComplaint,
  listMyComplaints,
  listReceivedComplaints,
} from '@/services/socialService'
import type { Complaint, ComplaintAgainstMe } from '@/types/platform'

vi.mock('@/services/socialService', () => ({
  createComplaint: vi.fn(),
  listMyComplaints: vi.fn(),
  listReceivedComplaints: vi.fn(),
}))

const mockedMine = vi.mocked(listMyComplaints)
const mockedReceived = vi.mocked(listReceivedComplaints)
const mockedCreate = vi.mocked(createComplaint)

function mine(overrides: Partial<Complaint> = {}): Complaint {
  return {
    id: 'k'.repeat(24),
    user_id: 'r'.repeat(24),
    subject: 'Late appointment',
    description: 'The lawyer joined very late.',
    status: 'IN_PROGRESS',
    reporter_response: 'Thanks for letting us know, we are on it.',
    reporter_responded_at: '2026-05-01T10:00:00Z',
    created_at: '2026-05-01T09:00:00Z',
    ...overrides,
  }
}

function againstMe(overrides: Partial<ComplaintAgainstMe> = {}): ComplaintAgainstMe {
  return {
    id: 'j'.repeat(24),
    subject: 'No show',
    description: 'The client did not attend the consultation.',
    status: 'RESOLVED',
    reported_response: 'We reviewed this complaint and took action.',
    reported_responded_at: '2026-05-02T10:00:00Z',
    created_at: '2026-05-02T09:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ComplaintsPage />
    </QueryClientProvider>,
  )
}

describe('ComplaintsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedReceived.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
  })

  it('shows the admin reply on complaints I filed', async () => {
    mockedMine.mockResolvedValue({ items: [mine()], total: 1, page: 1, page_size: 20 })

    renderPage()

    expect(await screen.findByText('Late appointment')).toBeTruthy()
    expect(screen.getByText('Thanks for letting us know, we are on it.')).toBeTruthy()
  })

  it('shows the admin reply on complaints filed about me', async () => {
    mockedMine.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    mockedReceived.mockResolvedValue({
      items: [againstMe()],
      total: 1,
      page: 1,
      page_size: 20,
    })

    renderPage()

    expect(await screen.findByText('No show')).toBeTruthy()
    expect(
      screen.getByText('We reviewed this complaint and took action.'),
    ).toBeTruthy()
  })

  it('submits a complaint and confirms success', async () => {
    mockedMine.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    mockedCreate.mockResolvedValue(mine())

    renderPage()
    const [subjectBox, descriptionBox] = screen.getAllByRole('textbox')
    await userEvent.type(subjectBox, 'Unprofessional conduct')
    await userEvent.type(descriptionBox, 'The lawyer behaved unprofessionally.')
    await userEvent.click(screen.getByRole('button', { name: /submit complaint/i }))

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledTimes(1))
    expect(mockedCreate).toHaveBeenCalledWith({
      subject: 'Unprofessional conduct',
      description: 'The lawyer behaved unprofessionally.',
    })
    expect(await screen.findByText(/complaint submitted successfully/i)).toBeTruthy()
  })
})
