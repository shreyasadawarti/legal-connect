import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuthStore } from '@/stores/authStore'
import { getMyProfile, updateMyProfile, type ProfileUpdatePayload } from '@/services/userService'

export default function ProfilePage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)

  const { isLoading, isError } = useQuery({
    queryKey: ['profile'],
    queryFn: getMyProfile,
  })

  const [name, setName] = useState(typeof user?.name === 'string' ? user.name : '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [city, setCity] = useState(user?.profile?.city ?? '')
  const [bio, setBio] = useState(user?.profile?.bio ?? '')
  const [language, setLanguage] = useState(user?.preferred_language ?? '')
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: (payload: ProfileUpdatePayload) => updateMyProfile(payload),
    onSuccess: (data) => {
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setUser(data)
    },
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSuccess(false)
    mutation.mutate({ name, phone: phone || undefined, city: city || undefined, bio: bio || undefined, preferred_language: language || undefined })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    )
  }

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
        <form noValidate onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Full name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Phone</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">City</label>
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Preferred language</label>
            <input
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled={mutation.isPending}
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
