import api from '@/services/api'
import type { LoginRequest, RegisterRequest, User, UserRole } from '@/types/user'

export async function login(email: string, password: string): Promise<User> {
  const { data } = await api.post<{ user: User; access_token: string; refresh_token: string }>(
    '/auth/login',
    { email, password } satisfies LoginRequest,
  )
  storeTokens(data)
  return data.user
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } finally {
    clearTokens()
  }
}

export async function register(payload: RegisterRequest): Promise<User> {
  const { data } = await api.post<{ user: User; access_token: string; refresh_token: string }>(
    '/auth/register',
    payload,
  )
  storeTokens(data)
  return data.user
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function forgotPassword(email: string): Promise<void> {
  await api.post('/auth/forgot-password', { email })
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await api.post('/auth/reset-password', { token, password })
}

export async function verifyEmail(token: string): Promise<void> {
  await api.post('/auth/verify-email', { token })
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await api.patch('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

function storeTokens(data: { access_token: string; refresh_token: string }): void {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
}

function clearTokens(): void {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export type { UserRole }
export type { LoginRequest, RegisterRequest, User }
