import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Loader2, Mail } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '@/components/auth/AuthShell'
import { verifyEmail } from '@/services/authService'

export default function EmailVerificationPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        await verifyEmail(token)
        if (active) {
          queryClient.invalidateQueries()
          setStatus('success')
          setTimeout(() => navigate('/login'), 1500)
        }
      } catch (err) {
        if (active) {
          setStatus('error')
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          setError(detail ?? 'Unable to verify your email. The link may be invalid or expired.')
        }
      }
    })()
    return () => {
      active = false
    }
  }, [token, navigate, queryClient])

  return (
    <AuthShell title="Email verification" subtitle="Verifying your email address...">
      <div className="rounded-2xl border border-surface-200 bg-white p-6 text-center dark:border-surface-800 dark:bg-surface-800 sm:p-8">
        {status === 'loading' && (
          <>
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-brand-600" />
            <p className="mt-4 text-sm text-surface-600 dark:text-surface-300">Verifying...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
            <p className="mt-4 text-sm text-surface-600 dark:text-surface-300">
              Your email has been verified successfully!
            </p>
          </>
        )}
        {status === 'error' && (
          <>
            <Mail className="mx-auto h-12 w-12 text-red-500" />
            <p className="mt-4 text-sm text-surface-600 dark:text-surface-300">{error}</p>
            <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
              You can request a new verification link from the sign-in page.
            </p>
            <Link to="/login" className="mt-4 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </AuthShell>
  )
}
