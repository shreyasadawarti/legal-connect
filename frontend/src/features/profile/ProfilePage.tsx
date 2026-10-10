import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Trash2, Upload, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import UserAvatar from '@/components/UserAvatar'
import { useAuthStore } from '@/stores/authStore'
import {
  getMyProfile,
  removeProfilePicture,
  updateMyProfile,
  uploadProfilePicture,
  type ProfileUpdatePayload,
} from '@/services/userService'

const MAX_PICTURE_BYTES = 5 * 1024 * 1024
const ACCEPTED_PICTURE_TYPES = ['image/png', 'image/jpeg', 'image/webp']

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

  const [picture, setPicture] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [pictureError, setPictureError] = useState<string | null>(null)
  const [pictureSaved, setPictureSaved] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const savedPictureUrl = data?.profile_picture_url ?? null

  // Object URLs are revoked when the selection changes or the page unmounts, so
  // repeated previews do not leak blobs for the life of the session.
  useEffect(() => {
    if (!picture) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(picture)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [picture])

  const applyPictureUpdate = (updated: Awaited<ReturnType<typeof getMyProfile>>) => {
    setPicture(null)
    setPictureSaved(true)
    setPictureError(null)
    setUser(updated)
    queryClient.invalidateQueries({ queryKey: ['profile'] })
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadProfilePicture(file),
    onSuccess: applyPictureUpdate,
    onError: (err) => {
      setPictureSaved(false)
      setPictureError(errorMessage(err))
    },
  })

  const removeMutation = useMutation({
    mutationFn: () => removeProfilePicture(),
    onSuccess: applyPictureUpdate,
    onError: (err) => {
      setPictureSaved(false)
      setPictureError(errorMessage(err))
    },
  })

  const onPickPicture = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setPictureSaved(false)
    setPictureError(null)
    if (!file) {
      setPicture(null)
      return
    }
    // Mirrors the backend limits so an oversized or unsupported file is rejected
    // before an upload round trip.
    if (!ACCEPTED_PICTURE_TYPES.includes(file.type)) {
      setPicture(null)
      setPictureError('Choose a PNG, JPG, or WebP image.')
      return
    }
    if (file.size > MAX_PICTURE_BYTES) {
      setPicture(null)
      setPictureError('That image is too large. The maximum is 5 MB.')
      return
    }
    setPicture(file)
  }

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

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
        <h2 className="text-base font-semibold">Profile picture</h2>
        <div className="mt-4 flex items-center gap-4">
          <UserAvatar src={preview ?? savedPictureUrl} name={data?.name} size="xl" />
          <div className="min-w-0 flex-1">
            <input
              ref={fileInputRef}
              id="profile-picture"
              type="file"
              accept={ACCEPTED_PICTURE_TYPES.join(',')}
              onChange={onPickPicture}
              className="sr-only"
            />
            <label
              htmlFor="profile-picture"
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200"
            >
              <Upload className="h-4 w-4" />
              {picture ? 'Change image' : 'Choose image'}
            </label>
            <p className="mt-2 text-xs text-surface-500 dark:text-surface-400">
              PNG, JPG, or WebP up to 5 MB.
            </p>
          </div>
        </div>

        {pictureError && (
          <p className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {pictureError}
          </p>
        )}
        {pictureSaved && (
          <p className="mt-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Profile picture updated.
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => picture && uploadMutation.mutate(picture)}
            disabled={!picture || uploadMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploadMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Save picture
          </button>
          <button
            type="button"
            onClick={() => removeMutation.mutate()}
            disabled={!savedPictureUrl || removeMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200"
          >
            <Trash2 className="h-4 w-4" />
            Remove
          </button>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
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
        <div className="mt-6 flex items-center justify-between gap-3 rounded-2xl border border-brand-200 bg-brand-50 p-5 dark:border-brand-900 dark:bg-brand-900/20">
          <div className="flex min-w-0 items-center gap-3">
            <UserRound className="h-6 w-6 shrink-0 text-brand-600" />
            <div className="min-w-0">
              <p className="font-medium">Lawyer profile</p>
              <p className="text-sm text-surface-500 dark:text-surface-400">
                Manage your legal profile, categories, rates, and availability.
              </p>
            </div>
          </div>
          <Link
            to="/lawyer/profile"
            className="shrink-0 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Edit
          </Link>
        </div>
      )}
    </div>
  )
}