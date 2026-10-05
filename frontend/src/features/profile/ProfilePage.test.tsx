import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import ProfilePage from '@/features/profile/ProfilePage'
import { useAuthStore } from '@/stores/authStore'

vi.mock('@/services/userService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/userService')>()
  return {
    ...actual,
    getMyProfile: vi.fn(),
    updateMyProfile: vi.fn(),
  }
})

import { getMyProfile, updateMyProfile } from '@/services/userService'

const mockedGet = vi.mocked(getMyProfile)
const mockedUpdate = vi.mocked(updateMyProfile)

const profile = {
  id: 'a'.repeat(24),
  name: 'Test User',
  email: 'user@example.com',
  phone: '+91 98765 43210',
  role: 'user' as const,
  city: 'Pune',
  address: '12 Shivaji Nagar, Pune 411005',
  bio: 'Tenant dispute advice',
  preferred_language: 'en',
  is_email_verified: true,
  status: 'ACTIVE' as const,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderProfile() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProfilePage', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false })
    vi.clearAllMocks()
    mockedGet.mockResolvedValue({ ...profile })
    mockedUpdate.mockImplementation(async (payload) => ({ ...profile, ...payload }))
  })

  // Regression: the page used to read `user.profile.city`, a nested shape the API
  // never returned, so saved values rendered blank on every reload.
  it('seeds every field from the server response, not the auth store', async () => {
    renderProfile()

    await waitFor(() => {
      expect(screen.getByLabelText('Full name')).toHaveValue('Test User')
    })
    expect(screen.getByLabelText('Phone')).toHaveValue('+91 98765 43210')
    expect(screen.getByLabelText('City')).toHaveValue('Pune')
    expect(screen.getByLabelText('Residential address')).toHaveValue(
      '12 Shivaji Nagar, Pune 411005',
    )
    expect(screen.getByLabelText('Bio')).toHaveValue('Tenant dispute advice')
    expect(screen.getByLabelText('Preferred language')).toHaveValue('en')
  })

  it('shows email as read-only', async () => {
    renderProfile()

    await waitFor(() => expect(screen.getByLabelText('Email')).toBeInTheDocument())
    const email = screen.getByLabelText('Email')
    expect(email).toHaveValue('user@example.com')
    expect(email).toHaveAttribute('readonly')
  })

  it('sends the address and other edits on save', async () => {
    renderProfile()

    await waitFor(() => expect(screen.getByLabelText('Full name')).toHaveValue('Test User'))

    await userEvent.clear(screen.getByLabelText('City'))
    await userEvent.type(screen.getByLabelText('City'), 'Mumbai')
    await userEvent.clear(screen.getByLabelText('Residential address'))
    await userEvent.type(screen.getByLabelText('Residential address'), '9 Fort Road')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledTimes(1))
    expect(mockedUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ city: 'Mumbai', address: '9 Fort Road' }),
    )
    await screen.findByText(/profile updated successfully/i)
  })

  it('sends empty strings so a field can be cleared', async () => {
    renderProfile()

    await waitFor(() => expect(screen.getByLabelText('Bio')).toHaveValue('Tenant dispute advice'))

    await userEvent.clear(screen.getByLabelText('Bio'))
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledTimes(1))
    expect(mockedUpdate).toHaveBeenCalledWith(expect.objectContaining({ bio: '' }))
  })

  it('surfaces a failure instead of failing silently', async () => {
    mockedUpdate.mockRejectedValue({
      response: { data: { detail: 'Address is too long' } },
    })
    renderProfile()

    await waitFor(() => expect(screen.getByLabelText('Full name')).toHaveValue('Test User'))
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await screen.findByText(/address is too long/i)
    expect(screen.queryByText(/profile updated successfully/i)).not.toBeInTheDocument()
  })

  it('shows validation messages from the API', async () => {
    mockedUpdate.mockRejectedValue({
      response: { data: { detail: [{ msg: 'String should have at most 20 characters' }] } },
    })
    renderProfile()

    await waitFor(() => expect(screen.getByLabelText('Full name')).toHaveValue('Test User'))
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await screen.findByText(/at most 20 characters/i)
  })
})