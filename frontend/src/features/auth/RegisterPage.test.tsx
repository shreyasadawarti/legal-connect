import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import RegisterPage from '@/features/auth/RegisterPage'
import { useAuthStore } from '@/stores/authStore'

vi.mock('@/services/authService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/authService')>()
  return {
    ...actual,
    register: vi.fn(),
    resendVerification: vi.fn(),
  }
})

import { register, resendVerification } from '@/services/authService'

function renderRegister() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RegisterPage', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false })
    vi.clearAllMocks()
  })

  it('renders all required fields and role selector', () => {
    renderRegister()
    expect(screen.getByLabelText('Full name')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('validates password length and match', async () => {
    const user = userEvent.setup()
    renderRegister()
    await user.type(screen.getByLabelText('Full name'), 'Test User')
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'short')
    await user.type(screen.getByLabelText('Confirm password'), 'short')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument()
  })

  it('shows error when passwords do not match', async () => {
    const user = userEvent.setup()
    renderRegister()
    await user.type(screen.getByLabelText('Full name'), 'Test User')
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'StrongPass123')
    await user.type(screen.getByLabelText('Confirm password'), 'Different123')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument()
  })

  it('submits with valid data and selects role correctly', async () => {
    const user = userEvent.setup()
    vi.mocked(register).mockResolvedValue({
      id: 'u1',
      name: 'Test User',
      email: 'test@example.com',
      role: 'user',
      is_email_verified: false,
      status: 'ACTIVE',
      created_at: '',
      updated_at: '',
    } as never)
    renderRegister()
    await user.type(screen.getByLabelText('Full name'), 'Test User')
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'StrongPass123')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass123')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(register).toHaveBeenCalledWith({
      name: 'Test User',
      email: 'test@example.com',
      password: 'StrongPass123',
      phone: undefined,
      role: 'user',
    })
  })

  it('shows the check-your-email step after a successful registration', async () => {
    const user = userEvent.setup()
    vi.mocked(register).mockResolvedValue({
      id: 'u1',
      name: 'Test User',
      email: 'test@example.com',
      role: 'user',
      is_email_verified: false,
      status: 'ACTIVE',
      created_at: '',
      updated_at: '',
    } as never)
    renderRegister()
    await user.type(screen.getByLabelText('Full name'), 'Test User')
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'StrongPass123')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('heading', { name: /check your email/i })).toBeInTheDocument()
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /create account/i })).not.toBeInTheDocument()
  })

  it('resends the verification email from the check-your-email step', async () => {
    const user = userEvent.setup()
    vi.mocked(register).mockResolvedValue({
      id: 'u1',
      name: 'Test User',
      email: 'test@example.com',
      role: 'user',
      is_email_verified: false,
      status: 'ACTIVE',
      created_at: '',
      updated_at: '',
    } as never)
    vi.mocked(resendVerification).mockResolvedValue(undefined)
    renderRegister()
    await user.type(screen.getByLabelText('Full name'), 'Test User')
    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'StrongPass123')
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await user.click(await screen.findByRole('button', { name: /resend verification email/i }))
    expect(resendVerification).toHaveBeenCalledWith('test@example.com')
    expect(await screen.findByText(/sent again/i)).toBeInTheDocument()
  })
})
