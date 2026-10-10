import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { Menu, Moon, Scale, Sun, X } from 'lucide-react'

import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'

const NAV_LINKS = [
  { to: '/lawyers', label: 'Find Lawyers' },
  { to: '/how-it-works', label: 'How It Works' },
  { to: '/about', label: 'About' },
  { to: '/faq', label: 'FAQ' },
]

export default function PublicLayout() {
  const { isAuthenticated } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

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

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-surface-200 bg-white/80 backdrop-blur dark:border-surface-800 dark:bg-surface-900/80">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-2 px-4 sm:px-6">
          <Link
            to="/"
            className="flex items-center gap-2 text-base font-bold text-brand-700 dark:text-brand-400 sm:text-lg"
          >
            <Scale className="h-6 w-6" />
            Legal Connect
          </Link>
          <nav className="hidden items-center gap-6 text-sm font-medium text-surface-700 dark:text-surface-200 md:flex">
            {NAV_LINKS.map((link) => (
              <Link key={link.to} to={link.to} className="hover:text-brand-600">
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-1.5 sm:gap-3">
            <button
              onClick={toggleTheme}
              aria-label="Toggle dark mode"
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
            >
              {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
            </button>
            <Link
              to={isAuthenticated ? '/dashboard' : '/login'}
              className="rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              {isAuthenticated ? 'Dashboard' : 'Sign In'}
            </Link>
            <button
              onClick={() => setMobileNavOpen((v) => !v)}
              aria-label={mobileNavOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileNavOpen}
              className="rounded-lg p-2 text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800 md:hidden"
            >
              {mobileNavOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
        {mobileNavOpen && (
          <nav className="border-t border-surface-200 px-4 pb-3 pt-1 dark:border-surface-800 md:hidden">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="block rounded-lg px-3 py-2.5 text-sm font-medium text-surface-700 hover:bg-surface-100 dark:text-surface-200 dark:hover:bg-surface-800"
              >
                {link.label}
              </Link>
            ))}
            <Link
              to="/contact"
              className="block rounded-lg px-3 py-2.5 text-sm font-medium text-surface-700 hover:bg-surface-100 dark:text-surface-200 dark:hover:bg-surface-800"
            >
              Contact
            </Link>
          </nav>
        )}
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-surface-200 bg-surface-100 py-8 dark:border-surface-800 dark:bg-surface-900">
        <div className="mx-auto max-w-7xl px-4 text-center text-sm text-surface-600 dark:text-surface-400 sm:px-6">
          <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            <Link to="/how-it-works" className="hover:text-brand-600 dark:hover:text-brand-400">
              How It Works
            </Link>
            <Link to="/about" className="hover:text-brand-600 dark:hover:text-brand-400">
              About
            </Link>
            <Link to="/faq" className="hover:text-brand-600 dark:hover:text-brand-400">
              FAQ
            </Link>
            <Link to="/contact" className="hover:text-brand-600 dark:hover:text-brand-400">
              Contact
            </Link>
            <Link to="/privacy" className="hover:text-brand-600 dark:hover:text-brand-400">
              Privacy
            </Link>
            <Link to="/terms" className="hover:text-brand-600 dark:hover:text-brand-400">
              Terms
            </Link>
          </nav>
          <p className="mt-4">© {new Date().getFullYear()} Legal Connect. All rights reserved.</p>
          <p className="mt-1 text-xs">
            Legal Connect provides general legal information, not legal advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
