import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Loader2, MapPin, MessageSquare, Star } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import UserAvatar from '@/components/UserAvatar'
import BookAppointmentSection from '@/features/appointments/BookAppointmentSection'
import ReportLawyerSection from '@/features/lawyers/ReportLawyerSection'
import { getLawyerProfile } from '@/services/lawyerService'
import { listLawyerReviews } from '@/services/socialService'

export default function LawyerProfilePage() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()

  const { data: lawyer, isLoading, isError } = useQuery({
    queryKey: ['lawyer', userId],
    queryFn: () => getLawyerProfile(userId!),
    enabled: Boolean(userId),
  })

  const { data: reviews } = useQuery({
    queryKey: ['lawyer-reviews', userId],
    queryFn: () => listLawyerReviews(userId!),
    enabled: Boolean(userId),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (isError || !lawyer) {
    return (
      <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
        Could not load this lawyer profile.
      </p>
    )
  }

  return (
    <div>
      <Link
        to="/lawyers"
        className="inline-flex items-center gap-1 text-sm text-surface-500 hover:text-surface-700 dark:text-surface-400"
      >
        <ArrowLeft className="h-4 w-4" /> Back to results
      </Link>

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-4">
                <UserAvatar src={lawyer.profile_picture_url} name={lawyer.name} size="xl" />
                <div>
                  <h1 className="text-2xl font-bold">{lawyer.name}</h1>
                <div className="mt-2 flex items-center gap-3 text-sm text-surface-500 dark:text-surface-400">
                  <span className="flex items-center gap-1">
                    <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                    {lawyer.avg_rating.toFixed(1)} ({lawyer.rating_count})
                  </span>
                  {lawyer.city && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" /> {lawyer.city}
                    </span>
                  )}
                </div>
                </div>
              </div>
              {lawyer.is_verified && (
                <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700 dark:bg-green-900/40 dark:text-green-400">
                  Verified
                </span>
              )}
            </div>

            <div className="mt-4 flex flex-wrap gap-1.5">
              {lawyer.categories.map((c) => (
                <span
                  key={c}
                  className="rounded-full bg-brand-50 px-3 py-1 text-xs text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
                >
                  {c.replace('_', ' ')}
                </span>
              ))}
            </div>

            <p className="mt-4 whitespace-pre-wrap text-sm text-surface-600 dark:text-surface-300">
              {lawyer.bio || 'This lawyer has not added a bio yet.'}
            </p>

            <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-surface-500 dark:text-surface-400">Experience</dt>
                <dd className="font-medium">{lawyer.years_of_experience} years</dd>
              </div>
              <div>
                <dt className="text-surface-500 dark:text-surface-400">Hourly rate</dt>
                <dd className="font-medium">
                  {lawyer.hourly_rate > 0 ? `₹${lawyer.hourly_rate}/hr` : 'Not set'}
                </dd>
              </div>
              <div>
                <dt className="text-surface-500 dark:text-surface-400">Languages</dt>
                <dd className="font-medium">{lawyer.languages.length ? lawyer.languages.join(', ') : '—'}</dd>
              </div>
            </dl>
          </div>

          <div className="mt-6 rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
            <h2 className="text-lg font-semibold">Client reviews</h2>
            {!reviews || reviews.items.length === 0 ? (
              <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">No reviews yet.</p>
            ) : (
              <div className="mt-4 space-y-4">
                {reviews.items.map((review) => (
                  <div key={review.id} className="border-t border-surface-200 pt-4 dark:border-surface-700">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{review.reviewer_name}</span>
                      <span className="flex items-center gap-1 text-sm">
                        <Star className="h-4 w-4 fill-amber-400 text-amber-400" /> {review.rating}
                      </span>
                    </div>
                    {review.comment && (
                      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">{review.comment}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-1">
          <button
            onClick={() =>
              navigate(`/chat?start=${lawyer.user_id}&name=${encodeURIComponent(lawyer.name)}`)
            }
            className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-brand-600 bg-white px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50 dark:bg-surface-800 dark:text-brand-300 dark:hover:bg-brand-900/20"
          >
            <MessageSquare className="h-4 w-4" /> Message
          </button>
          <BookAppointmentSection lawyer={lawyer} />
          <ReportLawyerSection lawyerUserId={lawyer.user_id} />
        </div>
      </div>
    </div>
  )
}
