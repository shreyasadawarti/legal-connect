import { useQuery } from '@tanstack/react-query'
import { Loader2, MapPin, Search, Star } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import UserAvatar from '@/components/UserAvatar'
import { searchLawyers } from '@/services/lawyerService'
import type { LawyerProfile, LegalCategory } from '@/types/platform'

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

export default function LawyerListPage() {
  const [searchParams] = useSearchParams()
  const initialCategory = searchParams.get('category') ?? ''

  const [q, setQ] = useState('')
  const [category, setCategory] = useState(initialCategory)
  const [city, setCity] = useState('')
  const [minRating, setMinRating] = useState('')
  const [applied, setApplied] = useState({ q: '', category: initialCategory, city: '', minRating: '' })

  const { data, isLoading, isError } = useQuery({
    queryKey: ['lawyers', applied],
    queryFn: () =>
      searchLawyers({
        q: applied.q || undefined,
        category: applied.category || undefined,
        city: applied.city || undefined,
        min_rating: applied.minRating ? Number(applied.minRating) : undefined,
        page_size: 50,
      }),
  })

  const apply = () => {
    setApplied({ q: q.trim(), category, city: city.trim(), minRating })
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Find a Lawyer</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Search verified legal professionals by practice area or location.
      </p>

      <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-surface-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search name, specialty"
              className="w-full rounded-lg border border-surface-300 bg-surface-50 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
            />
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          >
            <option value="">All categories</option>
            {CATEGORY_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {c.replace('_', ' ')}
              </option>
            ))}
          </select>
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="City"
            className="rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
          <select
            value={minRating}
            onChange={(e) => setMinRating(e.target.value)}
            className="rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          >
            <option value="">Min rating</option>
            <option value="4">4+ stars</option>
            <option value="3">3+ stars</option>
            <option value="2">2+ stars</option>
          </select>
        </div>
        <div className="mt-3 flex justify-end">
          <button
            onClick={apply}
            className="w-full rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 sm:w-auto"
          >
            Search
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}
      {isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load lawyers. Please try again.
        </p>
      )}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <p className="mt-8 rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
          No lawyers found matching your criteria.
        </p>
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((lawyer: LawyerProfile) => (
            <Link
              key={lawyer.user_id}
              to={`/lawyers/${lawyer.user_id}`}
              className="rounded-2xl border border-surface-200 bg-white p-5 transition hover:shadow-md dark:border-surface-800 dark:bg-surface-800"
            >
              <div className="flex items-start gap-3">
                <UserAvatar src={lawyer.profile_picture_url} name={lawyer.name} size="lg" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold">{lawyer.name}</h3>
                    {lawyer.is_verified && (
                      <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">
                        Verified
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
                    <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                    <span>{lawyer.avg_rating.toFixed(1)}</span>
                    <span>({lawyer.rating_count})</span>
                  </div>
                </div>
              </div>
              {lawyer.city && (
                <div className="mt-2 flex items-center gap-1 text-sm text-surface-500 dark:text-surface-400">
                  <MapPin className="h-4 w-4" />
                  {lawyer.city}
                </div>
              )}
              <div className="mt-3 flex flex-wrap gap-1.5">
                {lawyer.categories.map((c) => (
                  <span
                    key={c}
                    className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
                  >
                    {c.replace('_', ' ')}
                  </span>
                ))}
              </div>
              {lawyer.hourly_rate > 0 && (
                <p className="mt-3 text-sm font-semibold text-brand-700 dark:text-brand-300">
                  ₹{lawyer.hourly_rate}/hr
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
