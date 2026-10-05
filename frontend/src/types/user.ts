export type UserRole = 'user' | 'lawyer' | 'admin'

export type UserStatus = 'ACTIVE' | 'SUSPENDED' | 'DEACTIVATED'

export interface UserProfile {
  bio?: string
  city?: string
  address?: string
  avatar_url?: string
  date_of_birth?: string
}

export interface User {
  id: string
  name: string
  email: string
  phone?: string
  role: UserRole
  profile?: UserProfile
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
