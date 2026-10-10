import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import ResetPasswordPage from '@/features/auth/ResetPasswordPage'

vi.mock('@/services/authService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/authService')>()
  return { ...actual, resetPassword: vi.fn() }
})

import { resetPassword } from '@/services/authService'

function renderReset(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <ResetPasswordPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows an invalid-link message when the token is missing', () => {
    renderReset('/reset-password')
    expect(screen.getByRole('heading', { name: /invalid link/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /request a new link/i })).toBeInTheDocument()
  })

  it('confirms success and links back to sign in after resetting', async () => {
    const user = userEvent.setup()
    vi.mocked(resetPassword).mockResolvedValue(undefined)
    renderReset('/reset-password?token=abc123')

    await user.type(screen.getByLabelText('New password'), 'NewPass123')
    await user.type(screen.getByLabelText('Confirm password'), 'NewPass123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(resetPassword).toHaveBeenCalledWith('abc123', 'NewPass123')
    expect(await screen.findByText(/reset successfully/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /^sign in$/i })).toBeInTheDocument()
  })

  it('shows the API error when the reset token is rejected', async () => {
    const user = userEvent.setup()
    vi.mocked(resetPassword).mockRejectedValue({
      response: { data: { detail: 'This reset link is invalid or has expired.' } },
    })
    renderReset('/reset-password?token=expired')

    await user.type(screen.getByLabelText('New password'), 'NewPass123')
    await user.type(screen.getByLabelText('Confirm password'), 'NewPass123')
    await user.click(screen.getByRole('button', { name: /reset password/i }))

    expect(await screen.findByText(/invalid or has expired/i)).toBeInTheDocument()
  })
})
