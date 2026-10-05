import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuthStore } from '@/stores/authStore'
import { getMyProfile, updateMyProfile, type ProfileUpdatePayload } from '@/services/userService'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d) => (d as { msg?: string }).msg)
      .filter(Boolean)
      .join(', ') || 'Some fields were rejected.'
  }
  return 'Could not save your profile. Please try again.'
}

export default function ProfilePage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['profile'],
    queryFn: getMyProfile,
  })

  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [city, setCity] = useState('')
  const [address, setAddress] = useState('')
  const [bio, setBio] = useState('')
  const [language, setLanguage] = useState('')
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // The form is seeded from the server response rather than the auth store.
  // The store copy is only refreshed on login and after a save, so it can be
  // stale or missing fields that the profile endpoint returns authoritatively.
  useEffect(() => {
    if (!data) return
    setName(data.name ?? '')
    setPhone(data.phone ?? '')
    setCity(data.city ?? '')
    setAddress(data.address ?? '')
    setBio(data.bio ?? '')
    setLanguage(data.preferred_language ?? '')
  }, [data])

  const mutation = useMutation({
    mutationFn: (payload: ProfileUpdatePayload) => updateMyProfile(payload),
    onSuccess: (updated) => {
      setError(null)
      setSuccess(true)
      setUser(updated)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
    onError: (err) => {
      setSuccess(false)
      setError(errorMessage(err))
    },
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSuccess(false)
    setError(null)
    // Empty strings are sent deliberately: the backend ignores `None` but stores
    // `''`, which is what lets a user clear a field they previously filled in.
    mutation.mutate({
      name: name.trim(),
      phone: phone.trim(),
      city: city.trim(),
      address: address.trim(),
      bio: bio.trim(),
      preferred_language: language.trim(),
    })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    )
  }

  const email = data?.email ?? user?.email ?? ''

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold">Profile</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Manage your personal information.
      </p>

      {isError && (
        <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load your profile.
        </p>
      )}

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
        {success && (
          <p className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Profile updated successfully.
          </p>
        )}
        {error && (
          <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {error}
          </p>
        )}
        <form noValidate onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="profile-email" className="mb-1 block text-sm font-medium">
              Email
            </label>
            <input
              id="profile-email"
              value={email}
              readOnly
              disabled
              className="w-full cursor-not-allowed rounded-lg border border-surface-300 bg-surface-100 px-3 py-2 text-sm text-surface-500 outline-none dark:border-surface-700 dark:bg-surface-900 dark:text-surface-400"
            />
            <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
              Your sign-in address cannot be changed here.
            </p>
          </div>
          <div>
            <label htmlFor="profile-name" className="mb-1 block text-sm font-medium">
              Full name
            </label>
            <input
              id="profile-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label htmlFor="profile-phone" className="mb-1 block text-sm font-medium">
              Phone
            </label>
            <input
              id="profile-phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label htmlFor="profile-city" className="mb-1 block text-sm font-medium">
              City
            </label>
            <input
              id="profile-city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label htmlFor="profile-address" className="mb-1 block text-sm font-medium">
              Residential address
            </label>
            <textarea
              id="profile-address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              rows={2}
              placeholder="Street, area, city, postal code"
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label htmlFor="profile-language" className="mb-1 block text-sm font-medium">
              Preferred language
            </label>
            <input
              id="profile-language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label htmlFor="profile-bio" className="mb-1 block text-sm font-medium">
              Bio
            </label>
            <textarea
              id="profile-bio"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled={mutation.isPending || name.trim().length === 0}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {mutation.isPending ? 'Saving…' : 'Save changes'}
          </button>
        </form>
      </div>

      {user?.role === 'lawyer' && (
        <div className="mt-6 flex items-center justify-between rounded-2xl border border-brand-200 bg-brand-50 p-5 dark:border-brand-900 dark:bg-brand-900/20">
          <div className="flex items-center gap-3">
            <UserRound className="h-6 w-6 text-brand-600" />
            <div>
              <p className="font-medium">Lawyer profile</p>
              <p className="text-sm text-surface-500 dark:text-surface-400">
                Manage your legal profile, categories, rates, and availability.
              </p>
            </div>
          </div>
          <Link
            to="/lawyer/profile"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Edit
          </Link>
        </div>
      )}
    </div>
  )
}