import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import AuthShell from '@/components/auth/AuthShell'
import PasswordInput from '@/components/PasswordInput'
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
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: (data: Form) => resetPassword(token, data.password),
    onSuccess: () => {
      queryClient.clear()
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Unable to reset password. The link may be invalid or expired.')
    },
  })

  if (!token) {
    return (
      <AuthShell title="Invalid link" subtitle="This password reset link is missing a token.">
        <div className="rounded-2xl border border-surface-200 bg-white p-6 text-center dark:border-surface-800 dark:bg-surface-800 sm:p-8">
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
        <div className="rounded-2xl border border-surface-200 bg-white p-6 text-center dark:border-surface-800 dark:bg-surface-800 sm:p-8">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
          <p className="mt-4 text-sm text-surface-600 dark:text-surface-300">
            Your password has been reset successfully. You can now sign in with your new password.
          </p>
          <Link to="/login" className="mt-5 inline-block rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700">
            Sign in
          </Link>
        </div>
      ) : (
        <form noValidate onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4 rounded-2xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-800 sm:p-6">
          {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">{error}</div>}
          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="password">New password</label>
            <PasswordInput id="password" {...register('password')} placeholder="Min 8 characters" />
            {errors.password && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="confirmPassword">Confirm password</label>
            <PasswordInput id="confirmPassword" {...register('confirmPassword')} placeholder="Re-enter password" />
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
