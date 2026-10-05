import { create } from 'zustand'

import { getMe, login, logout } from '@/services/authService'
import type { User } from '@/types/user'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  fetchCurrentUser: () => Promise<void>
  setUser: (user: User | null) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: Boolean(localStorage.getItem('access_token')),
  isLoading: false,

  login: async (email, password) => {
    const user = await login(email, password)
    set({ user, isAuthenticated: true, isLoading: false })
    return user
  },

  logout: async () => {
    try {
      await logout()
    } catch {
      // ignore network errors on logout
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  fetchCurrentUser: async () => {
    set({ isLoading: true })
    try {
      const me = await getMe()
      set({ user: me, isAuthenticated: true, isLoading: false })
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  setUser: (user) => set({ user, isAuthenticated: Boolean(user) }),
}))
