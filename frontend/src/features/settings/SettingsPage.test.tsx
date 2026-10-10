import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import SettingsPage from '@/features/settings/SettingsPage'
import { useAuthStore } from '@/stores/authStore'
import type { UserPreferences } from '@/types/platform'

vi.mock('@/services/userService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/userService')>()
  return {
    ...actual,
    getMyProfile: vi.fn(),
    updateMyProfile: vi.fn(),
    uploadProfilePicture: vi.fn(),
    removeProfilePicture: vi.fn(),
    listMyBlocks: vi.fn(),
    unblockUser: vi.fn(),
    deleteMyAccount: vi.fn(),
  }
})

vi.mock('@/services/preferenceService', () => ({
  getMyPreferences: vi.fn(),
  updateMyPreferences: vi.fn(),
}))

vi.mock('@/services/authService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/authService')>()
  return { ...actual, changePassword: vi.fn(), logout: vi.fn() }
})

import { changePassword, logout } from '@/services/authService'
import { getMyPreferences, updateMyPreferences } from '@/services/preferenceService'
import {
  deleteMyAccount,
  getMyProfile,
  listMyBlocks,
  unblockUser,
} from '@/services/userService'

const mockedProfile = vi.mocked(getMyProfile)
const mockedPrefs = vi.mocked(getMyPreferences)
const mockedSavePrefs = vi.mocked(updateMyPreferences)
const mockedBlocks = vi.mocked(listMyBlocks)
const mockedUnblock = vi.mocked(unblockUser)
const mockedChangePassword = vi.mocked(changePassword)
const mockedLogout = vi.mocked(logout)
const mockedDelete = vi.mocked(deleteMyAccount)

const profile = {
  id: 'a'.repeat(24),
  name: 'Test User',
  email: 'user@example.com',
  role: 'user' as const,
  city: 'Pune',
  is_email_verified: true,
  status: 'ACTIVE' as const,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const preferences: UserPreferences = {
  notifications: {
    email_appointments: true,
    email_messages: true,
    email_reviews: true,
    push_appointments: true,
    push_messages: true,
    push_complaints: true,
  },
  interests: [],
  privacy: { show_profile: true, show_online_status: true },
}

function renderSettings() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    useAuthStore.setState({
      user: { ...profile },
      isAuthenticated: true,
      isLoading: false,
    })
    mockedProfile.mockResolvedValue({ ...profile })
    mockedPrefs.mockResolvedValue(structuredClone(preferences))
    mockedSavePrefs.mockImplementation(async (patch) => ({ ...preferences, ...patch }))
    mockedBlocks.mockResolvedValue([])
    mockedUnblock.mockResolvedValue(undefined)
    mockedChangePassword.mockResolvedValue(undefined)
    mockedLogout.mockResolvedValue(undefined)
    mockedDelete.mockResolvedValue(undefined)
  })

  it('shows citizen tabs instead of lawyer tabs', async () => {
    renderSettings()
    expect(screen.getByRole('button', { name: 'Interests' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Professional' })).not.toBeInTheDocument()
  })

  it('shows the professional tab for lawyers', async () => {
    useAuthStore.setState({ user: { ...profile, role: 'lawyer' } })
    renderSettings()
    expect(screen.getByRole('button', { name: 'Professional' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Interests' })).not.toBeInTheDocument()
  })

  it('saves a notification toggle', async () => {
    renderSettings()
    await userEvent.click(screen.getByRole('button', { name: 'Notifications' }))

    const toggle = await screen.findByRole('switch', { name: 'Message push' })
    await userEvent.click(toggle)
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockedSavePrefs).toHaveBeenCalledTimes(1))
    expect(mockedSavePrefs.mock.calls[0][0].notifications?.push_messages).toBe(false)
    await screen.findByText(/preferences saved/i)
  })

  it('saves selected interests', async () => {
    renderSettings()
    await userEvent.click(screen.getByRole('button', { name: 'Interests' }))

    await userEvent.click(await screen.findByRole('checkbox', { name: 'Family' }))
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(mockedSavePrefs).toHaveBeenCalledTimes(1))
    expect(mockedSavePrefs.mock.calls[0][0].interests).toEqual(['family'])
  })

  it('lists blocked accounts and unblocks one', async () => {
    mockedBlocks.mockResolvedValue([{ id: 'b'.repeat(24), name: 'Blocked Bob', role: 'lawyer' }])
    renderSettings()
    await userEvent.click(screen.getByRole('button', { name: 'Privacy' }))

    await screen.findByText('Blocked Bob')
    await userEvent.click(screen.getByRole('button', { name: /unblock/i }))

    await waitFor(() => expect(mockedUnblock).toHaveBeenCalledWith('b'.repeat(24)))
  })

  it('rejects mismatched new passwords before calling the API', async () => {
    renderSettings()
    await userEvent.click(screen.getByRole('button', { name: 'Security' }))

    await userEvent.type(screen.getByLabelText('Current password'), 'OldPass123')
    await userEvent.type(screen.getByLabelText('New password'), 'NewPass123')
    await userEvent.type(screen.getByLabelText('Confirm new password'), 'Different1')
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))

    await screen.findByText(/do not match/i)
    expect(mockedChangePassword).not.toHaveBeenCalled()
  })

  it('changes the password when the form is valid', async () => {
    renderSettings()
    await userEvent.click(screen.getByRole('button', { name: 'Security' }))

    await userEvent.type(screen.getByLabelText('Current password'), 'OldPass123')
    await userEvent.type(screen.getByLabelText('New password'), 'NewPass123')
    await userEvent.type(screen.getByLabelText('Confirm new password'), 'NewPass123')
    await userEvent.click(screen.getByRole('button', { name: /update password/i }))

    await waitFor(() =>
      expect(mockedChangePassword).toHaveBeenCalledWith('OldPass123', 'NewPass123'),
    )
    await screen.findByText(/password changed successfully/i)
  })

  it('deletes the account after password confirmation', async () => {
    renderSettings()
    await userEvent.click(screen.getByRole('button', { name: 'Account' }))

    await userEvent.click(screen.getByRole('button', { name: /delete my account/i }))
    await userEvent.type(screen.getByLabelText('Password'), 'MyPass123')
    await userEvent.click(screen.getByRole('button', { name: /^delete account$/i }))

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('MyPass123'))
    await waitFor(() => expect(mockedLogout).toHaveBeenCalled())
  })
})
