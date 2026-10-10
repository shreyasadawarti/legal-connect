import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Calendar,
  Clock,
  FileText,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  MessageSquare,
  Moon,
  Scale,
  Settings,
  Sparkles,
  Sun,
  User as UserIcon,
  X,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import IncomingCallBanner from '@/features/chat/IncomingCallBanner'
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
    { to: '/complaints', label: 'Complaints', icon: AlertTriangle },
    { to: '/ai-assistant', label: 'AI Assistant', icon: Sparkles },
    { to: '/nearby-lawyers', label: 'Nearby Lawyers', icon: MapPin },
    { to: '/profile', label: 'Profile', icon: UserIcon },
    { to: '/settings', label: 'Settings', icon: Settings },
  ],
  lawyer: [
    { to: '/lawyer/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/lawyer/appointments', label: 'Appointments', icon: Calendar },
    { to: '/lawyer/availability', label: 'Availability', icon: Clock },
    { to: '/lawyer/documents', label: 'Documents', icon: FileText },
    { to: '/lawyer/chat', label: 'Chat', icon: MessageSquare },
    { to: '/complaints', label: 'Complaints', icon: AlertTriangle },
    { to: '/lawyer/earnings', label: 'Earnings', icon: Scale },
    { to: '/profile', label: 'Profile', icon: UserIcon },
    { to: '/settings', label: 'Settings', icon: Settings },
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

const DASHBOARD_ROUTES = ['/dashboard', '/lawyer/dashboard', '/admin/dashboard']

function SidebarNav({
  items,
  onNavigate,
}: {
  items: { to: string; label: string; icon: React.ElementType }[]
  onNavigate?: () => void
}) {
  return (
    <nav className="space-y-1 p-3">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={DASHBOARD_ROUTES.includes(item.to)}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
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
  )
}

export default function DashboardLayout() {
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const role = user?.role ?? 'user'
  const items = NAV_ITEMS[role]

  useEffect(() => {
    setMobileNavOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!mobileNavOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileNavOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileNavOpen])

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
        <SidebarNav items={items} />
      </aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-slate-900/50"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="absolute left-0 top-0 flex h-full w-64 max-w-[80vw] flex-col border-r border-surface-200 bg-white shadow-xl dark:border-surface-800 dark:bg-surface-800"
          >
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-surface-200 pl-4 pr-2 dark:border-surface-800">
              <div className="flex items-center gap-2">
                <Scale className="h-6 w-6 text-brand-600" />
                <span className="text-lg font-bold text-surface-900 dark:text-surface-50">
                  Legal Connect
                </span>
              </div>
              <button
                onClick={() => setMobileNavOpen(false)}
                aria-label="Close navigation"
                className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <SidebarNav items={items} onNavigate={() => setMobileNavOpen(false)} />
            </div>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-3 border-b border-surface-200 bg-white px-4 dark:border-surface-800 dark:bg-surface-800 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation"
              aria-expanded={mobileNavOpen}
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700 md:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="truncate text-sm font-medium text-surface-600 dark:text-surface-300">
              {user?.name}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
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
              aria-label="Logout"
              className="inline-flex items-center gap-2 rounded-lg border border-surface-300 px-3 py-1.5 text-sm text-surface-600 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-700"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>
        <main className="flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
      <IncomingCallBanner />
    </div>
  )
}
