import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import LoginPage from '@/features/auth/LoginPage'
import { useAuthStore } from '@/stores/authStore'

vi.mock('@/services/authService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/authService')>()
  return {
    ...actual,
    login: vi.fn(),
  }
})

import { login } from '@/services/authService'

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false })
    vi.clearAllMocks()
  })

  it('renders the sign-in form', () => {
    renderLogin()
    expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows validation errors on empty submit', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByText('Enter a valid email')).toBeInTheDocument()
    expect(await screen.findByText('Password is required')).toBeInTheDocument()
  })

  it('shows an error for an invalid email', async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByText('Enter a valid email')).toBeInTheDocument()
  })

  it('calls login on valid submit', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockResolvedValue({
      id: 'u1',
      name: 'Test',
      email: 'test@example.com',
      role: 'user',
      is_email_verified: false,
      status: 'ACTIVE',
      created_at: '',
      updated_at: '',
    } as never)
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(login).toHaveBeenCalled())
  })

  it('shows an error message when login fails', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockRejectedValue({
      response: { data: { detail: 'Invalid email or password' } },
    })
    renderLogin()
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrongpass123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByText(/Invalid email or password/i)).toBeInTheDocument()
  })
})
