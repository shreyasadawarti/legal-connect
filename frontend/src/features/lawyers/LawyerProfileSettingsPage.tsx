import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock, Loader2, Plus, Trash2, Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import {
  createMyLawyerProfile,
  getMyLawyerProfile,
  linkVerificationDocument,
  updateMyLawyerProfile,
} from '@/services/lawyerService'
import { uploadDocument } from '@/services/documentService'
import type { AvailabilitySlot, LegalCategory } from '@/types/platform'

const CATEGORY_OPTIONS: LegalCategory[] = [
  'family',
  'criminal',
  'civil',
  'corporate',
  'property',
  'tax',
  'labor',
  'intellectual_property',
  'contract',
  'personal_injury',
  'immigration',
  'other',
]

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function LawyerProfileSettingsPage() {
  const queryClient = useQueryClient()

  const { data: profile, isLoading } = useQuery({
    queryKey: ['my-lawyer-profile'],
    queryFn: getMyLawyerProfile,
  })

  const [bio, setBio] = useState('')
  const [years, setYears] = useState(0)
  const [categories, setCategories] = useState<LegalCategory[]>([])
  const [specializations, setSpecializations] = useState('')
  const [languages, setLanguages] = useState('')
  const [rate, setRate] = useState('')
  const [city, setCity] = useState('')
  const [availability, setAvailability] = useState<AvailabilitySlot[]>([])
  const [hasProfile, setHasProfile] = useState(false)
  const [saved, setSaved] = useState(false)

  const [proofFile, setProofFile] = useState<File | null>(null)
  const [proofBusy, setProofBusy] = useState(false)
  const [proofError, setProofError] = useState('')
  const [proofSaved, setProofSaved] = useState(false)
  const proofInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!profile) return
    setHasProfile(true)
    setBio(profile.bio ?? '')
    setYears(profile.years_of_experience ?? 0)
    setCategories(profile.categories ?? [])
    setSpecializations((profile.specializations ?? []).join(', '))
    setLanguages((profile.languages ?? []).join(', '))
    setRate(profile.hourly_rate ? String(profile.hourly_rate) : '')
    setCity(profile.city ?? '')
    setAvailability(profile.availability ?? [])
  }, [profile])

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        bio,
        years_of_experience: years,
        categories,
        specializations: specializations.split(',').map((s) => s.trim()).filter(Boolean),
        languages: languages.split(',').map((s) => s.trim()).filter(Boolean),
        hourly_rate: rate ? Number(rate) : 0,
        city: city || undefined,
        availability,
      }
      return hasProfile ? updateMyLawyerProfile(payload) : createMyLawyerProfile(payload)
    },
    onSuccess: () => {
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['my-lawyer-profile'] })
    },
  })

  const toggleCategory = (c: LegalCategory) => {
    setCategories((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]))
  }

  const uploadProof = async () => {
    if (!proofFile) return
    setProofBusy(true)
    setProofError('')
    try {
      const doc = await uploadDocument(proofFile, 'Lawyer verification document', undefined, 'verification')
      await linkVerificationDocument(doc.id)
      setProofFile(null)
      setProofSaved(true)
      if (proofInputRef.current) proofInputRef.current.value = ''
      queryClient.invalidateQueries({ queryKey: ['my-lawyer-profile'] })
    } catch (err) {
      setProofError(err instanceof Error ? err.message : 'Could not upload your documentary proof.')
    } finally {
      setProofBusy(false)
    }
  }

  const updateSlot = (i: number, patch: Partial<AvailabilitySlot>) => {
    setAvailability((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)))
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
      <h1 className="text-2xl font-bold">Lawyer profile</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Set up your professional profile, practice areas, and availability.
      </p>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
        {saved && (
          <p className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Profile saved successfully.
          </p>
        )}
        {mutation.isError && (
          <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            Could not save your profile.
          </p>
        )}

        <form noValidate onSubmit={(e) => { e.preventDefault(); setSaved(false); mutation.mutate() }} className="space-y-5">
          <div>
            <label className="mb-1 block text-sm font-medium">Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Years of experience</label>
              <input
                type="number"
                min={0}
                max={70}
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Hourly rate (₹)</label>
              <input
                type="number"
                min={0}
                value={rate}
                onChange={(e) => setRate(e.target.value)}
                className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
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
            <label className="mb-2 block text-sm font-medium">Practice areas</label>
            <div className="flex flex-wrap gap-2">
              {CATEGORY_OPTIONS.map((c) => {
                const active = categories.includes(c)
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => toggleCategory(c)}
                    className={active
                      ? 'rounded-full bg-brand-600 px-3 py-1 text-xs font-medium text-white'
                      : 'rounded-full border border-surface-300 px-3 py-1 text-xs hover:bg-surface-100 dark:border-surface-700 dark:hover:bg-surface-700'}
                  >
                    {c.replace('_', ' ')}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Specializations (comma separated)</label>
              <input
                value={specializations}
                onChange={(e) => setSpecializations(e.target.value)}
                className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Languages (comma separated)</label>
              <input
                value={languages}
                onChange={(e) => setLanguages(e.target.value)}
                className="w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
              />
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="flex items-center gap-1.5 text-sm font-medium">
                <Clock className="h-4 w-4 text-brand-600" /> Weekly availability
              </label>
              <button
                type="button"
                onClick={() => setAvailability((prev) => [...prev, { day_of_week: 0, start_time: '09:00', end_time: '17:00' }])}
                className="inline-flex items-center gap-1 rounded-lg border border-surface-300 px-2.5 py-1 text-xs hover:bg-surface-100 dark:border-surface-700 dark:hover:bg-surface-700"
              >
                <Plus className="h-3.5 w-3.5" /> Add slot
              </button>
            </div>
            {availability.length === 0 ? (
              <p className="rounded-lg bg-surface-50 px-3 py-2 text-sm text-surface-500 dark:bg-surface-900 dark:text-surface-400">
                No availability set. Clients will still be able to request appointments.
              </p>
            ) : (
              <div className="space-y-2">
                {availability.map((slot, i) => (
                  <div key={i} className="grid grid-cols-[2fr_1fr_1fr_auto] items-center gap-2">
                    <select
                      value={slot.day_of_week}
                      onChange={(e) => updateSlot(i, { day_of_week: Number(e.target.value) })}
                      className="rounded-lg border border-surface-300 bg-surface-50 px-2 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                    >
                      {DAY_NAMES.map((d, day) => (
                        <option key={d} value={day}>{d}</option>
                      ))}
                    </select>
                    <input
                      type="time"
                      value={slot.start_time}
                      onChange={(e) => updateSlot(i, { start_time: e.target.value })}
                      className="rounded-lg border border-surface-300 bg-surface-50 px-2 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                    />
                    <input
                      type="time"
                      value={slot.end_time}
                      onChange={(e) => updateSlot(i, { end_time: e.target.value })}
                      className="rounded-lg border border-surface-300 bg-surface-50 px-2 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
                    />
                    <button
                      type="button"
                      onClick={() => setAvailability((prev) => prev.filter((_, idx) => idx !== i))}
                      className="rounded-lg p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                      aria-label="Remove slot"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {mutation.isPending ? 'Saving…' : hasProfile ? 'Save changes' : 'Create profile'}
          </button>
        </form>
      </div>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
        <div className="mb-2 flex items-center gap-2">
          <Upload className="h-4 w-4 text-brand-600" />
          <h2 className="text-lg font-semibold">Documentary proof</h2>
        </div>
        <p className="text-sm text-surface-600 dark:text-surface-300">
          Upload a valid license or certificate (PDF, PNG, or JPG) so an admin can verify your profile.
        </p>

        {proofSaved && (
          <p className="mt-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
            Documentary proof uploaded successfully.
          </p>
        )}
        {proofError && (
          <p className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {proofError}
          </p>
        )}

        {profile?.verification_document_id && (
          <p className="mt-3 rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            Documentary proof on file.
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            ref={proofInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            disabled={!hasProfile || proofBusy}
            onChange={(e) => {
              setProofFile(e.target.files?.[0] ?? null)
              setProofSaved(false)
              setProofError('')
            }}
            className="block w-full max-w-sm text-sm text-surface-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-brand-700 hover:file:bg-brand-100 dark:text-surface-300 dark:file:bg-surface-700 dark:file:text-brand-300"
          />
          <button
            type="button"
            onClick={uploadProof}
            disabled={!proofFile || !hasProfile || proofBusy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {proofBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {proofBusy ? 'Uploading…' : 'Upload proof'}
          </button>
        </div>

        {!hasProfile && (
          <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
            Save your lawyer profile first, then upload your documentary proof.
          </p>
        )}
        {hasProfile && profile?.verification_status === 'PENDING_VERIFICATION' && !profile.verification_document_id && (
          <p className="mt-3 text-sm text-amber-600 dark:text-amber-400">
            Verification is pending and no documentary proof is uploaded yet. Upload one to help admins verify your profile faster.
          </p>
        )}
      </div>
    </div>
  )
}
