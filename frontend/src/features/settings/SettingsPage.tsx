import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Trash2, UserX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import ConfirmDialog from '@/components/ConfirmDialog'
import PasswordInput from '@/components/PasswordInput'
import ProfilePage from '@/features/profile/ProfilePage'
import { changePassword } from '@/services/authService'
import { getMyPreferences, updateMyPreferences } from '@/services/preferenceService'
import { deleteMyAccount, listMyBlocks, unblockUser } from '@/services/userService'
import { useAuthStore } from '@/stores/authStore'
import type { LegalCategory, UserPreferences } from '@/types/platform'

const CATEGORY_OPTIONS: { value: LegalCategory; label: string }[] = [
  { value: 'family', label: 'Family' },
  { value: 'criminal', label: 'Criminal' },
  { value: 'civil', label: 'Civil' },
  { value: 'corporate', label: 'Corporate' },
  { value: 'property', label: 'Property' },
  { value: 'tax', label: 'Tax' },
  { value: 'labor', label: 'Labor' },
  { value: 'intellectual_property', label: 'Intellectual Property' },
  { value: 'contract', label: 'Contract' },
  { value: 'personal_injury', label: 'Personal Injury' },
  { value: 'immigration', label: 'Immigration' },
  { value: 'other', label: 'Other' },
]

const NOTIFICATION_OPTIONS: { key: string; label: string; hint: string }[] = [
  { key: 'email_appointments', label: 'Appointment emails', hint: 'Booking, confirmation, and changes.' },
  { key: 'email_messages', label: 'Message emails', hint: 'When someone sends you a chat message.' },
  { key: 'email_reviews', label: 'Review emails', hint: 'When you receive a new review.' },
  { key: 'push_appointments', label: 'Appointment push', hint: 'In-app alerts for appointments.' },
  { key: 'push_messages', label: 'Message push', hint: 'In-app alerts for new messages.' },
  { key: 'push_complaints', label: 'Complaint push', hint: 'Updates on complaints and reports.' },
]

const PRIVACY_OPTIONS: { key: string; label: string; hint: string }[] = [
  { key: 'show_profile', label: 'Show my profile', hint: 'Let other members view your profile.' },
  { key: 'show_online_status', label: 'Show online status', hint: 'Display when you are active in chat.' },
]

type TabKey =
  | 'profile'
  | 'professional'
  | 'interests'
  | 'notifications'
  | 'privacy'
  | 'security'
  | 'account'

function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return (
      detail
        .map((d) => (d as { msg?: string }).msg)
        .filter(Boolean)
        .join(', ') || fallback
    )
  }
  return fallback
}

function Toggle({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
  hint?: string
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-lg border border-surface-200 px-4 py-3 dark:border-surface-700">
      <span>
        <span className="block text-sm font-medium">{label}</span>
        {hint && <span className="mt-0.5 block text-xs text-surface-500 dark:text-surface-400">{hint}</span>}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition ${
          checked ? 'bg-brand-600' : 'bg-surface-300 dark:bg-surface-600'
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
            checked ? 'left-[22px]' : 'left-0.5'
          }`}
        />
      </button>
    </label>
  )
}

export default function SettingsPage() {
  const role = useAuthStore((s) => s.user?.role)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'profile', label: 'Profile' },
    ...(role === 'lawyer' ? [{ key: 'professional' as TabKey, label: 'Professional' }] : []),
    ...(role === 'user' ? [{ key: 'interests' as TabKey, label: 'Interests' }] : []),
    { key: 'notifications', label: 'Notifications' },
    { key: 'privacy', label: 'Privacy' },
    { key: 'security', label: 'Security' },
    { key: 'account', label: 'Account' },
  ]

  const [active, setActive] = useState<TabKey>('profile')

  const prefsQuery = useQuery({ queryKey: ['my-preferences'], queryFn: getMyPreferences })
  const [draft, setDraft] = useState<UserPreferences | null>(null)
  const [prefsNotice, setPrefsNotice] = useState<string | null>(null)
  const [prefsError, setPrefsError] = useState<string | null>(null)

  useEffect(() => {
    if (prefsQuery.data) setDraft(prefsQuery.data)
  }, [prefsQuery.data])

  const savePrefs = useMutation({
    mutationFn: (next: UserPreferences) => updateMyPreferences(next),
    onSuccess: (saved) => {
      setPrefsError(null)
      setPrefsNotice('Preferences saved.')
      setDraft(saved)
      queryClient.setQueryData(['my-preferences'], saved)
    },
    onError: (err) => {
      setPrefsNotice(null)
      setPrefsError(errorMessage(err, 'Could not save your preferences. Please try again.'))
    },
  })

  const blocksQuery = useQuery({ queryKey: ['my-blocks'], queryFn: listMyBlocks })
  const unblockMutation = useMutation({
    mutationFn: (userId: string) => unblockUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-blocks'] }),
  })

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwdNotice, setPwdNotice] = useState<string | null>(null)
  const [pwdError, setPwdError] = useState<string | null>(null)

  const passwordMutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: async () => {
      setPwdError(null)
      setPwdNotice('Password changed successfully.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await logout()
      navigate('/login?passwordChanged=1')
    },
    onError: (err) => {
      setPwdNotice(null)
      setPwdError(errorMessage(err, 'Could not change your password. Please try again.'))
    },
  })

  const onSubmitPassword = (e: React.FormEvent) => {
    e.preventDefault()
    setPwdNotice(null)
    setPwdError(null)
    if (newPassword.length < 8) {
      setPwdError('New password must be at least 8 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPwdError('New passwords do not match.')
      return
    }
    passwordMutation.mutate()
  }

  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const deleteMutation = useMutation({
    mutationFn: () => deleteMyAccount(deletePassword),
    onSuccess: async () => {
      setDeleteOpen(false)
      await logout()
      navigate('/')
    },
    onError: (err) => {
      setDeleteError(errorMessage(err, 'Could not delete your account. Please try again.'))
    },
  })

  const updateDraft = (patch: Partial<UserPreferences>) => {
    setPrefsNotice(null)
    setPrefsError(null)
    setDraft((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  const loadingSpinner = (
    <div className="flex justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
    </div>
  )

  const prefsFeedback = (
    <>
      {prefsNotice && (
        <p className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
          {prefsNotice}
        </p>
      )}
      {prefsError && (
        <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {prefsError}
        </p>
      )}
    </>
  )

  const saveButton = (
    <button
      type="button"
      onClick={() => draft && savePrefs.mutate(draft)}
      disabled={savePrefs.isPending || !draft}
      className="mt-5 rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
    >
      {savePrefs.isPending ? 'Saving…' : 'Save changes'}
    </button>
  )

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold">Settings</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Manage your profile, notifications, privacy, and account security.
      </p>

      <div className="mt-6 flex flex-wrap gap-2 border-b border-surface-200 pb-3 dark:border-surface-800">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActive(tab.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              active === tab.key
                ? 'bg-brand-600 text-white'
                : 'text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {active === 'profile' && <ProfilePage />}

        {active === 'professional' && (
          <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
            <h2 className="text-base font-semibold">Professional details</h2>
            <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
              Manage your legal categories, consultation fees, bio, and weekly availability.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                to="/lawyer/profile"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Edit professional profile
              </Link>
              <Link
                to="/lawyer/availability"
                className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-surface-700 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200"
              >
                Manage availability
              </Link>
            </div>
          </div>
        )}

        {active === 'interests' && (
          <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
            {prefsQuery.isLoading || !draft ? loadingSpinner : (
              <>
                <h2 className="text-base font-semibold">Legal interests</h2>
                <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
                  Pick the areas you care about so we can personalise lawyer recommendations.
                </p>
                {prefsFeedback}
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {CATEGORY_OPTIONS.map((option) => {
                    const checked = draft.interests.includes(option.value)
                    return (
                      <label
                        key={option.value}
                        className="flex cursor-pointer items-center gap-3 rounded-lg border border-surface-200 px-4 py-3 text-sm dark:border-surface-700"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            updateDraft({
                              interests: checked
                                ? draft.interests.filter((c) => c !== option.value)
                                : [...draft.interests, option.value],
                            })
                          }
                          className="h-4 w-4 rounded border-surface-300 text-brand-600 focus:ring-brand-500"
                        />
                        {option.label}
                      </label>
                    )
                  })}
                </div>
                {saveButton}
              </>
            )}
          </div>
        )}

        {active === 'notifications' && (
          <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
            {prefsQuery.isLoading || !draft ? loadingSpinner : (
              <>
                <h2 className="text-base font-semibold">Notification preferences</h2>
                <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
                  Choose how you want to hear about activity on your account.
                </p>
                {prefsFeedback}
                <div className="mt-4 space-y-2">
                  {NOTIFICATION_OPTIONS.map((option) => (
                    <Toggle
                      key={option.key}
                      label={option.label}
                      hint={option.hint}
                      checked={draft.notifications[option.key] ?? true}
                      onChange={(value) =>
                        updateDraft({
                          notifications: { ...draft.notifications, [option.key]: value },
                        })
                      }
                    />
                  ))}
                </div>
                {saveButton}
              </>
            )}
          </div>
        )}

        {active === 'privacy' && (
          <div className="space-y-6">
            <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
              {prefsQuery.isLoading || !draft ? loadingSpinner : (
                <>
                  <h2 className="text-base font-semibold">Privacy</h2>
                  {prefsFeedback}
                  <div className="mt-4 space-y-2">
                    {PRIVACY_OPTIONS.map((option) => (
                      <Toggle
                        key={option.key}
                        label={option.label}
                        hint={option.hint}
                        checked={draft.privacy[option.key] ?? true}
                        onChange={(value) =>
                          updateDraft({ privacy: { ...draft.privacy, [option.key]: value } })
                        }
                      />
                    ))}
                  </div>
                  {saveButton}
                </>
              )}
            </div>

            <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
              <h2 className="flex items-center gap-2 text-base font-semibold">
                <UserX className="h-4 w-4" /> Blocked accounts
              </h2>
              <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
                Blocked people cannot message you in chat.
              </p>
              <div className="mt-4 space-y-2">
                {blocksQuery.isLoading ? (
                  <div className="flex justify-center py-6">
                    <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
                  </div>
                ) : blocksQuery.data && blocksQuery.data.length > 0 ? (
                  blocksQuery.data.map((blocked) => (
                    <div
                      key={blocked.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-surface-200 px-4 py-3 dark:border-surface-700"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{blocked.name}</p>
                        <p className="text-xs capitalize text-surface-500 dark:text-surface-400">
                          {blocked.role}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => unblockMutation.mutate(blocked.id)}
                        disabled={unblockMutation.isPending}
                        className="shrink-0 rounded-lg border border-surface-300 px-3 py-1.5 text-sm font-medium text-surface-700 hover:bg-surface-50 disabled:opacity-60 dark:border-surface-700 dark:text-surface-200"
                      >
                        Unblock
                      </button>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-surface-500 dark:text-surface-400">
                    You have not blocked anyone.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {active === 'security' && (
          <div className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800 sm:p-6">
            <h2 className="text-base font-semibold">Change password</h2>
            <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
              Use a strong password you do not reuse elsewhere.
            </p>
            {pwdNotice && (
              <p className="mt-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">
                {pwdNotice}
              </p>
            )}
            {pwdError && (
              <p className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
                {pwdError}
              </p>
            )}
            <form onSubmit={onSubmitPassword} className="mt-4 space-y-4">
              <div>
                <label htmlFor="current-password" className="mb-1 block text-sm font-medium">
                  Current password
                </label>
                <PasswordInput
                  id="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
              <div>
                <label htmlFor="new-password" className="mb-1 block text-sm font-medium">
                  New password
                </label>
                <PasswordInput
                  id="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label htmlFor="confirm-new-password" className="mb-1 block text-sm font-medium">
                  Confirm new password
                </label>
                <PasswordInput
                  id="confirm-new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
              <button
                type="submit"
                disabled={passwordMutation.isPending}
                className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {passwordMutation.isPending ? 'Updating…' : 'Update password'}
              </button>
            </form>
          </div>
        )}

        {active === 'account' && (
          <div className="rounded-2xl border border-red-200 bg-red-50/50 p-4 dark:border-red-900/50 dark:bg-red-900/10 sm:p-6">
            <h2 className="flex items-center gap-2 text-base font-semibold text-red-700 dark:text-red-300">
              <Trash2 className="h-4 w-4" /> Delete account
            </h2>
            <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
              This deactivates your account and removes your personal details. Your appointment and
              document history is retained in anonymised form for legal and audit purposes. This
              cannot be undone.
            </p>
            <button
              type="button"
              onClick={() => {
                setDeleteError(null)
                setDeletePassword('')
                setDeleteOpen(true)
              }}
              className="mt-4 rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              Delete my account
            </button>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteOpen}
        title="Delete your account?"
        description="Enter your password to confirm. This will deactivate your account immediately."
        confirmLabel="Delete account"
        danger
        isPending={deleteMutation.isPending}
        onClose={() => setDeleteOpen(false)}
        onConfirm={() => deleteMutation.mutate()}
      >
        <div className="mt-2">
          <label htmlFor="delete-password" className="mb-1 block text-sm font-medium">
            Password
          </label>
          <PasswordInput
            id="delete-password"
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
            autoComplete="current-password"
          />
          {deleteError && (
            <p className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {deleteError}
            </p>
          )}
        </div>
      </ConfirmDialog>
    </div>
  )
}
