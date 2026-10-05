import { Navigate, Outlet } from 'react-router-dom'

import { useAuthStore } from '@/stores/authStore'
import type { UserRole } from '@/types/user'

export default function RoleRoute({ roles }: { roles: UserRole[] }) {
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!user || !roles.includes(user.role)) {
    return <Navigate to={user?.role === 'lawyer' ? '/lawyer/dashboard' : '/dashboard'} replace />
  }

  return <Outlet />
}
