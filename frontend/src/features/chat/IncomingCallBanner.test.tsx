import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import IncomingCallBanner from '@/features/chat/IncomingCallBanner'
import { useAuthStore } from '@/stores/authStore'
import type { SocketEvent } from '@/types/platform'

const { listeners, emit } = vi.hoisted(() => {
  const listeners: Array<(event: SocketEvent) => void> = []
  return {
    listeners,
    emit: (event: SocketEvent) => listeners.forEach((l) => l(event)),
  }
})

vi.mock('@/services/chatSocket', () => ({
  chatSocket: {
    ready: () => true,
    connect: vi.fn(),
    subscribe: (cb: (event: SocketEvent) => void) => {
      listeners.push(cb)
      return () => {
        const i = listeners.indexOf(cb)
        if (i >= 0) listeners.splice(i, 1)
      }
    },
    startCall: vi.fn(),
    endCall: vi.fn(),
  },
}))

const ME = 'c'.repeat(24)
const PEER = 'l'.repeat(24)
const APPOINTMENT_ID = 'a'.repeat(24)

function LocationProbe() {
  const location = useLocation()
  return <span data-testid="location">{location.pathname}</span>
}

function renderBanner(initialPath = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/dashboard" element={<IncomingCallBanner />} />
        <Route path="/video-call/:appointmentId" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  )
}

function callRequest(overrides: Partial<Extract<SocketEvent, { type: 'call-request' }>> = {}) {
  return {
    type: 'call-request' as const,
    appointment_id: APPOINTMENT_ID,
    from_user_id: PEER,
    from_name: 'Test Lawyer',
    ...overrides,
  }
}

describe('IncomingCallBanner', () => {
  beforeEach(() => {
    listeners.length = 0
    localStorage.setItem('access_token', 'test-token')
    useAuthStore.setState({
      user: {
        id: ME,
        name: 'Test User',
        email: 'user@example.com',
        role: 'user',
        status: 'ACTIVE',
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
    })
  })

  it('shows a Receive Video Call button when the peer rings this appointment', async () => {
    renderBanner()
    act(() => emit(callRequest()))
    expect(await screen.findByRole('button', { name: /receive video call/i })).toBeTruthy()
    expect(screen.getByText('Test Lawyer')).toBeTruthy()
    expect(screen.getByText('Incoming video call')).toBeTruthy()
  })

  it('joins the appointment call when the button is clicked', async () => {
    renderBanner()
    act(() => emit(callRequest()))
    await userEvent.click(await screen.findByRole('button', { name: /receive video call/i }))
    expect((await screen.findByTestId('location')).textContent).toBe(
      `/video-call/${APPOINTMENT_ID}`,
    )
  })

  it('hides the banner when the call ends', async () => {
    renderBanner()
    act(() => emit(callRequest()))
    expect(await screen.findByRole('button', { name: /receive video call/i })).toBeTruthy()
    act(() => emit({ type: 'call-end', appointment_id: APPOINTMENT_ID, from_user_id: PEER }))
    expect(screen.queryByRole('button', { name: /receive video call/i })).toBeNull()
  })

  it('ignores signals started by the current user', async () => {
    renderBanner()
    act(() => emit(callRequest({ from_user_id: ME })))
    expect(screen.queryByRole('button', { name: /receive video call/i })).toBeNull()
  })

  it('does not show a banner while already in that call', async () => {
    renderBanner(`/video-call/${APPOINTMENT_ID}`)
    act(() => emit(callRequest()))
    expect(screen.queryByRole('button', { name: /receive video call/i })).toBeNull()
  })
})
