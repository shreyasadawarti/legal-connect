import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Loader2, Lock } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import AuthShell from '@/components/auth/AuthShell'
import { resetPassword } from '@/services/authService'

const schema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
type Form = z.infer<typeof schema>

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: (data: Form) => resetPassword(token, data.password),
    onSuccess: () => {
      queryClient.clear()
      navigate('/login')
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Unable to reset password. The link may be invalid or expired.')
    },
  })

  if (!token) {
    return (
      <AuthShell title="Invalid link" subtitle="This password reset link is missing a token.">
        <div className="rounded-2xl border border-surface-200 bg-white p-8 text-center dark:border-surface-800 dark:bg-surface-800">
          <p className="text-sm text-surface-600 dark:text-surface-300">Please use the link from your email.</p>
          <Link to="/forgot-password" className="mt-4 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
            Request a new link
          </Link>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell title="Set a new password" subtitle="Enter your new password below." footer={(
      <Link to="/login" className="font-medium text-brand-600 hover:text-brand-700">Back to sign in</Link>
    )}>
      {mutation.isSuccess ? (
        <div className="rounded-2xl border border-surface-200 bg-white p-8 text-center dark:border-surface-800 dark:bg-surface-800">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
          <p className="mt-4 text-sm text-surface-600 dark:text-surface-300">Password updated. Redirecting to sign in...</p>
        </div>
      ) : (
        <form noValidate onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4 rounded-2xl border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-800 dark:bg-surface-800">
          {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">{error}</div>}
          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="password">New password</label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-surface-400" />
              <input id="password" type="password" {...register('password')} placeholder="Min 8 characters" className="w-full rounded-lg border border-surface-300 bg-surface-50 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900" />
            </div>
            {errors.password && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="confirmPassword">Confirm password</label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-surface-400" />
              <input id="confirmPassword" type="password" {...register('confirmPassword')} placeholder="Re-enter password" className="w-full rounded-lg border border-surface-300 bg-surface-50 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900" />
            </div>
            {errors.confirmPassword && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.confirmPassword.message}</p>}
          </div>
          <button type="submit" disabled={mutation.isPending} className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Reset password
          </button>
        </form>
      )}
    </AuthShell>
  )
}
