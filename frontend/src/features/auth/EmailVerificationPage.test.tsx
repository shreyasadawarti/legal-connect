import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import EmailVerificationPage from '@/features/auth/EmailVerificationPage'

vi.mock('@/services/authService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/authService')>()
  return { ...actual, verifyEmail: vi.fn() }
})

import { verifyEmail } from '@/services/authService'

function renderVerify(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <EmailVerificationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EmailVerificationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('verifies the token and shows success', async () => {
    vi.mocked(verifyEmail).mockResolvedValue(undefined)
    renderVerify('/verify-email?token=good')

    expect(await screen.findByText(/verified successfully/i)).toBeInTheDocument()
    expect(verifyEmail).toHaveBeenCalledWith('good')
  })

  it('shows the failure detail and a route back to sign in', async () => {
    vi.mocked(verifyEmail).mockRejectedValue({
      response: { data: { detail: 'This verification link is invalid or has expired.' } },
    })
    renderVerify('/verify-email?token=bad')

    expect(await screen.findByText(/invalid or has expired/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to sign in/i })).toBeInTheDocument()
  })
})
