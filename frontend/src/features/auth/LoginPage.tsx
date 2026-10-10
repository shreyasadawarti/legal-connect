import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Loader2, Mail } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import PasswordInput from '@/components/PasswordInput'
import { resendVerification } from '@/services/authService'
import { useAuthStore } from '@/stores/authStore'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const passwordChanged = searchParams.get('passwordChanged') === '1'
  const login = useAuthStore((s) => s.login)
  const [error, setError] = useState<string | null>(null)
  const [unverified, setUnverified] = useState(false)
  const [resent, setResent] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const emailValue = watch('email')

  const mutation = useMutation({
    mutationFn: (data: LoginForm) => login(data.email, data.password),
    onSuccess: (user) => {
      if (user.role === 'admin') navigate('/admin/dashboard')
      else navigate('/dashboard')
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { status?: number; data?: { detail?: string } } })
        ?.response
      const detail = response?.data?.detail
      setError(detail ?? 'Login failed. Please try again.')
      setUnverified(response?.status === 403 && /verif/i.test(detail ?? ''))
    },
  })

  const resendMutation = useMutation({
    mutationFn: () => resendVerification(emailValue),
    onSuccess: () => setResent(true),
  })

  const onSubmit = (data: LoginForm) => {
    setError(null)
    setUnverified(false)
    setResent(false)
    mutation.mutate(data)
  }

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
          Sign in to your Legal Connect account
        </p>
      </div>

      <form
        noValidate
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4 rounded-2xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-800 sm:p-6"
      >
        {passwordChanged && !error && (
          <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Your password was changed. Please sign in again.
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            <p>{error}</p>
            {unverified && (
              <div className="mt-3">
                {resent ? (
                  <p className="text-green-700 dark:text-green-300">
                    Verification email sent again. Please check your inbox.
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={() => resendMutation.mutate()}
                    disabled={resendMutation.isPending || !emailValue}
                    className="font-semibold underline disabled:opacity-60"
                  >
                    Resend verification email
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="email">
            Email
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-surface-400" />
            <input
              id="email"
              type="email"
              {...register('email')}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-surface-300 bg-surface-50 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          {errors.email && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium" htmlFor="password">
            Password
          </label>
          <PasswordInput
            id="password"
            {...register('password')}
            placeholder="••••••••"
          />
          {errors.password && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>
          )}
        </div>

        <div className="flex items-center justify-between text-sm">
          <Link to="/forgot-password" className="font-medium text-brand-600 hover:text-brand-700">
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          {mutation.isPending ? 'Signing in...' : 'Sign In'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-surface-600 dark:text-surface-300">
        Don't have an account?{' '}
        <Link to="/register" className="font-medium text-brand-600 hover:text-brand-700">
          Register
        </Link>
      </p>

      <p className="mt-3 text-center text-sm text-surface-500 dark:text-surface-400">
        <Link to="/admin/login" className="font-medium text-brand-600 hover:text-brand-700">
          Admin? Sign in to the admin portal
        </Link>
      </p>
    </div>
  )
}
