import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Loader2, Mail, MailCheck, Scale, User } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'

import PasswordInput from '@/components/PasswordInput'
import { register, resendVerification } from '@/services/authService'
import type { UserRole } from '@/types/user'

const registerSchema = z
  .object({
    name: z.string().min(2, 'Name is required'),
    email: z.string().email('Enter a valid email'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[0-9]/, 'Password must contain a number')
      .regex(/[a-zA-Z]/, 'Password must contain a letter'),
    confirmPassword: z.string(),
    phone: z.string().optional(),
    role: z.enum(['user', 'lawyer']),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type RegisterForm = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const [error, setError] = useState<string | null>(null)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)
  const [resent, setResent] = useState(false)

  const {
    register: field,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: 'user' },
  })

  const role = watch('role')

  const mutation = useMutation({
    mutationFn: (data: RegisterForm) =>
      register({
        name: data.name,
        email: data.email,
        password: data.password,
        phone: data.phone || undefined,
        role: data.role as UserRole,
      }),
    onSuccess: (user) => {
      setSubmittedEmail(user.email)
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Registration failed. Please try again.')
    },
  })

  const resendMutation = useMutation({
    mutationFn: (email: string) => resendVerification(email),
    onSuccess: () => setResent(true),
  })

  const onSubmit = (data: RegisterForm) => {
    setError(null)
    mutation.mutate(data)
  }

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold">
          {submittedEmail ? 'Check your email' : 'Create your account'}
        </h1>
        <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
          {submittedEmail ? 'Verify your address to activate your account' : 'Join Legal Connect today'}
        </p>
      </div>

      {submittedEmail ? (
        <div className="rounded-2xl border border-surface-200 bg-white p-5 text-center shadow-sm dark:border-surface-800 dark:bg-surface-800 sm:p-6">
          <MailCheck className="mx-auto h-12 w-12 text-green-500" />
          <p className="mt-4 text-sm text-surface-600 dark:text-surface-300">
            We sent a verification link to <span className="font-medium">{submittedEmail}</span>.
            Click the link in that email to activate your account, then sign in.
          </p>
          {resent && (
            <p className="mt-3 rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
              Verification email sent again. Please check your inbox.
            </p>
          )}
          <div className="mt-5 flex flex-col gap-3">
            <button
              type="button"
              onClick={() => resendMutation.mutate(submittedEmail)}
              disabled={resendMutation.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-300 py-2.5 text-sm font-semibold hover:bg-surface-50 disabled:opacity-60 dark:border-surface-700 dark:hover:bg-surface-700"
            >
              {resendMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Resend verification email
            </button>
            <Link
              to="/login"
              className="text-sm font-medium text-brand-600 hover:text-brand-700"
            >
              Back to sign in
            </Link>
          </div>
        </div>
      ) : (
        <form
          noValidate
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 rounded-2xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-800 sm:p-6"
        >
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="name">
              Full name
            </label>
            <div className="relative">
              <User className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-surface-400" />
              <input
                id="name"
                type="text"
                {...field('name')}
                placeholder="Your name"
                className="w-full rounded-lg border border-surface-300 bg-surface-50 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
            {errors.name && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-surface-400" />
              <input
                id="email"
                type="email"
                {...field('email')}
                placeholder="you@example.com"
                className="w-full rounded-lg border border-surface-300 bg-surface-50 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
            {errors.email && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="phone">
              Phone (optional)
            </label>
            <input
              id="phone"
              type="tel"
              {...field('phone')}
              placeholder="+91 00000 00000"
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="password">
              Password
            </label>
            <PasswordInput
              id="password"
              {...field('password')}
              placeholder="Min 8 chars, with letters & numbers"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium" htmlFor="confirmPassword">
              Confirm password
            </label>
            <PasswordInput
              id="confirmPassword"
              {...field('confirmPassword')}
              placeholder="Re-enter password"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">I am a</label>
            <div className="grid grid-cols-2 gap-3">
              <label
                className={`flex cursor-pointer items-center gap-2 rounded-lg border p-3 text-sm transition ${
                  role === 'user'
                    ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-900/30'
                    : 'border-surface-300 dark:border-surface-700'
                }`}
              >
                <input type="radio" value="user" {...field('role')} className="sr-only" />
                <User className="h-5 w-5" />
                Citizen
              </label>
              <label
                className={`flex cursor-pointer items-center gap-2 rounded-lg border p-3 text-sm transition ${
                  role === 'lawyer'
                    ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-900/30'
                    : 'border-surface-300 dark:border-surface-700'
                }`}
              >
                <input type="radio" value="lawyer" {...field('role')} className="sr-only" />
                <Scale className="h-5 w-5" />
                Lawyer
              </label>
            </div>
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {mutation.isPending ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-surface-600 dark:text-surface-300">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand-600 hover:text-brand-700">
          Sign in
        </Link>
      </p>
    </div>
  )
}