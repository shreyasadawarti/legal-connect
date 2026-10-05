import {
  AlertTriangle,
  BarChart3,
  Calendar,
  FileText,
  LayoutDashboard,
  LogOut,
  MapPin,
  MessageSquare,
  Moon,
  Scale,
  Settings,
  Sparkles,
  Sun,
  User as UserIcon,
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import type { UserRole } from '@/types/user'

const NAV_ITEMS: Record<UserRole, { to: string; label: string; icon: React.ElementType }[]> = {
  user: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/lawyers', label: 'Find Lawyers', icon: Scale },
    { to: '/appointments', label: 'Appointments', icon: Calendar },
    { to: '/documents', label: 'Documents', icon: FileText },
    { to: '/chat', label: 'Chat', icon: MessageSquare },
    { to: '/ai-assistant', label: 'AI Assistant', icon: Sparkles },
    { to: '/nearby-lawyers', label: 'Nearby Lawyers', icon: MapPin },
    { to: '/profile', label: 'Profile', icon: UserIcon },
  ],
  lawyer: [
    { to: '/lawyer/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/lawyer/appointments', label: 'Appointments', icon: Calendar },
    { to: '/lawyer/availability', label: 'Availability', icon: Settings },
    { to: '/lawyer/documents', label: 'Documents', icon: FileText },
    { to: '/lawyer/chat', label: 'Chat', icon: MessageSquare },
    { to: '/lawyer/earnings', label: 'Earnings', icon: Scale },
    { to: '/profile', label: 'Profile', icon: UserIcon },
  ],
  admin: [
    { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/admin/lawyers', label: 'Lawyers', icon: Scale },
    { to: '/admin/users', label: 'Users', icon: UserIcon },
    { to: '/admin/appointments', label: 'Appointments', icon: Calendar },
    { to: '/admin/complaints', label: 'Complaints', icon: AlertTriangle },
    { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/admin/reports', label: 'Reports', icon: FileText },
    { to: '/admin/audit-logs', label: 'Audit Logs', icon: Settings },
    { to: '/profile', label: 'Profile', icon: UserIcon },
  ],
}

export default function DashboardLayout() {
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()

  const role = user?.role ?? 'user'
  const items = NAV_ITEMS[role]

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="flex min-h-screen bg-surface-50 dark:bg-surface-900">
      <aside className="hidden w-64 shrink-0 border-r border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800 md:block">
        <div className="flex h-16 items-center gap-2 border-b border-surface-200 px-6 dark:border-surface-800">
          <Scale className="h-6 w-6 text-brand-600" />
          <span className="text-lg font-bold text-surface-900 dark:text-surface-50">Legal Connect</span>
        </div>
        <nav className="space-y-1 p-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/dashboard' || item.to === '/lawyer/dashboard' || item.to === '/admin/dashboard'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
                    : 'text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700'
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-surface-200 bg-white px-6 dark:border-surface-800 dark:bg-surface-800">
          <div className="text-sm font-medium text-surface-600 dark:text-surface-300">
            {user?.name}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              aria-label="Toggle dark mode"
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700"
            >
              {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
            </button>
            <span className="hidden rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold uppercase text-brand-700 dark:bg-brand-900/40 dark:text-brand-400 sm:inline">
              {role}
            </span>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-lg border border-surface-300 px-3 py-1.5 text-sm text-surface-600 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-700"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
