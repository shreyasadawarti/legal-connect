import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LawyerReviewsPage from '@/features/lawyer/LawyerReviewsPage'
import { getMyLawyerProfile } from '@/services/lawyerService'
import { listLawyerReviews } from '@/services/socialService'
import type { Review } from '@/types/platform'

vi.mock('@/services/lawyerService', () => ({
  getMyLawyerProfile: vi.fn(),
}))
vi.mock('@/services/socialService', () => ({
  listLawyerReviews: vi.fn(),
}))

const mockedProfile = vi.mocked(getMyLawyerProfile)
const mockedReviews = vi.mocked(listLawyerReviews)

const LAWYER_ID = 'l'.repeat(24)

const profile = {
  user_id: LAWYER_ID,
  name: 'Ananya Sharma',
  email: 'lawyer@example.com',
  bio: 'Experienced family lawyer',
  years_of_experience: 5,
  categories: ['family' as const],
  specializations: ['Divorce'],
  languages: ['English'],
  hourly_rate: 100,
  city: 'Mumbai',
  availability: [],
  avg_rating: 4.5,
  rating_count: 2,
  verification_status: 'ACTIVE' as const,
  is_verified: true,
}

function review(overrides: Partial<Review> = {}): Review {
  return {
    id: 'r'.repeat(24),
    lawyer_id: LAWYER_ID,
    lawyer_name: 'Ananya Sharma',
    reviewer_id: 'c'.repeat(24),
    reviewer_name: 'Priya Verma',
    rating: 5,
    comment: 'Very helpful consultation.',
    created_at: '2026-05-02T10:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <LawyerReviewsPage />
    </QueryClientProvider>,
  )
}

describe('LawyerReviewsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedProfile.mockResolvedValue({ ...profile })
    mockedReviews.mockResolvedValue({
      items: [review()],
      total: 1,
      page: 1,
      page_size: 100,
    })
  })

  it('shows the rating summary from the lawyer profile', async () => {
    renderPage()
    expect(await screen.findByText('4.5')).toBeTruthy()
    expect(screen.getByText('2')).toBeTruthy()
  })

  it('lists citizen reviews with name, rating and comment', async () => {
    renderPage()
    expect(await screen.findByText('Priya Verma')).toBeTruthy()
    expect(screen.getByText('Very helpful consultation.')).toBeTruthy()
    expect(screen.getByText('5')).toBeTruthy()
  })

  it('fetches reviews for the lawyer’s own user id', async () => {
    renderPage()
    await waitFor(() => expect(mockedReviews).toHaveBeenCalledWith(LAWYER_ID, 100))
  })

  it('shows an empty state when there are no reviews', async () => {
    mockedReviews.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    mockedProfile.mockResolvedValue({ ...profile, avg_rating: 0, rating_count: 0 })
    renderPage()
    expect(await screen.findByText(/no reviews yet/i)).toBeTruthy()
  })

  it('surfaces an error banner when the reviews fail to load', async () => {
    mockedReviews.mockRejectedValue(new Error('network down'))
    renderPage()
    expect(await screen.findByText(/could not load your reviews/i)).toBeTruthy()
  })
})
