export type UserRole = 'user' | 'lawyer' | 'admin'

export type UserStatus = 'ACTIVE' | 'SUSPENDED' | 'DEACTIVATED'

/**
 * Mirrors the API's user document exactly: personal fields are flat, matching
 * `UserProfileResponse` on the backend. The lawyer-only professional fields
 * (categories, rate, verification) live in `LawyerProfile`, not here.
 */
export interface User {
  id: string
  name: string
  email: string
  phone?: string
  role: UserRole
city?: string
address?: string
profile_picture_url?: string
bio?: string
  preferred_language?: string
  is_email_verified: boolean
  status: UserStatus
  created_at: string
  updated_at: string
  last_login_at?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  name: string
  email: string
  password: string
  phone?: string
  role?: UserRole
}

export interface ApiError {
  detail?: string
  message?: string
}
