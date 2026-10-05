import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'

import ProtectedRoute from '@/components/auth/ProtectedRoute'
import RoleRoute from '@/components/auth/RoleRoute'
import { useAuthStore } from '@/stores/authStore'
import type { User } from '@/types/user'

const LoginStub = () => <div>Login page</div>
const CitizenStub = () => <div>Citizen dashboard</div>
const AdminStub = () => <div>Admin dashboard</div>

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginStub />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<RoleRoute roles={['user']} />}>
            <Route path="/dashboard" element={<CitizenStub />} />
          </Route>
          <Route element={<RoleRoute roles={['admin']} />}>
            <Route path="/admin/dashboard" element={<AdminStub />} />
          </Route>
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

function mockUser(role: 'user' | 'lawyer' | 'admin'): User {
  return {
    id: 'u1',
    name: 'Test User',
    email: 'test@example.com',
    role,
    is_email_verified: true,
    status: 'ACTIVE',
    created_at: '',
    updated_at: '',
  }
}

describe('route guards', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    })
    vi.clearAllMocks()
  })

  it('redirects unauthenticated users to /login', () => {
    renderAt('/dashboard')
    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('shows loading state while auth is loading', () => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: true })
    renderAt('/dashboard')
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('allows an authenticated user through RoleRoute for matching role', () => {
    useAuthStore.setState({
      user: mockUser('user'),
      isAuthenticated: true,
      isLoading: false,
    })
    renderAt('/dashboard')
    expect(screen.getByText('Citizen dashboard')).toBeInTheDocument()
  })

  it('redirects a user away from an admin-only route', () => {
    useAuthStore.setState({
      user: mockUser('user'),
      isAuthenticated: true,
      isLoading: false,
    })
    renderAt('/admin/dashboard')
    expect(screen.getByText('Citizen dashboard')).toBeInTheDocument()
  })

  it('allows an admin through the admin RoleRoute', () => {
    useAuthStore.setState({
      user: mockUser('admin'),
      isAuthenticated: true,
      isLoading: false,
    })
    renderAt('/admin/dashboard')
    expect(screen.getByText('Admin dashboard')).toBeInTheDocument()
  })
})
