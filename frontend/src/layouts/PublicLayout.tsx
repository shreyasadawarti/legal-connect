import { Link, Outlet } from 'react-router-dom'
import { Moon, Scale, Sun } from 'lucide-react'

import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'

export default function PublicLayout() {
  const { isAuthenticated } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-surface-200 bg-white/80 backdrop-blur dark:border-surface-800 dark:bg-surface-900/80">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold text-brand-700 dark:text-brand-400">
            <Scale className="h-6 w-6" />
            Legal Connect
          </Link>
          <nav className="hidden items-center gap-6 text-sm font-medium text-surface-700 dark:text-surface-200 md:flex">
            <Link to="/lawyers" className="hover:text-brand-600">Find Lawyers</Link>
            <Link to="/how-it-works" className="hover:text-brand-600">How It Works</Link>
            <Link to="/about" className="hover:text-brand-600">About</Link>
            <Link to="/faq" className="hover:text-brand-600">FAQ</Link>
          </nav>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              aria-label="Toggle dark mode"
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
            >
              {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
            </button>
            {isAuthenticated ? (
              <Link
                to="/dashboard"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Dashboard
              </Link>
            ) : (
              <Link
                to="/login"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-surface-200 bg-surface-100 py-8 dark:border-surface-800 dark:bg-surface-900">
        <div className="mx-auto max-w-7xl px-4 text-center text-sm text-surface-600 dark:text-surface-400 sm:px-6">
          <p>© {new Date().getFullYear()} Legal Connect. All rights reserved.</p>
          <p className="mt-1 text-xs">
            Legal Connect provides general legal information, not legal advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
