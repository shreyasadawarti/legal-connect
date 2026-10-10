import { useQuery } from '@tanstack/react-query'
import { Loader2, Star } from 'lucide-react'

import { getMyLawyerProfile } from '@/services/lawyerService'
import { listLawyerReviews } from '@/services/socialService'

const CARD_STYLE =
  'rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800'

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

export default function LawyerReviewsPage() {
  const {
    data: profile,
    isLoading: profileLoading,
    isError: profileError,
  } = useQuery({
    queryKey: ['my-lawyer-profile'],
    queryFn: getMyLawyerProfile,
  })

  const lawyerId = profile?.user_id

  const {
    data: reviews,
    isLoading: reviewsLoading,
    isError: reviewsError,
  } = useQuery({
    queryKey: ['lawyer-reviews', lawyerId],
    queryFn: () => listLawyerReviews(lawyerId!, 100),
    enabled: Boolean(lawyerId),
  })

  const isLoading = profileLoading || (Boolean(lawyerId) && reviewsLoading)
  const isError = profileError || reviewsError

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (isError || !profile) {
    return (
      <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
        Could not load your reviews.
      </p>
    )
  }

  const items = reviews?.items ?? []

  return (
    <div>
      <h1 className="text-2xl font-bold">Reviews &amp; ratings</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        What citizens are saying about your consultations.
      </p>

      <div className={`mt-6 ${CARD_STYLE}`}>
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <p className="text-sm text-surface-500 dark:text-surface-400">Average rating</p>
            <p className="mt-1 flex items-center gap-1 text-3xl font-bold">
              <Star className="h-6 w-6 fill-amber-400 text-amber-400" />
              {profile.avg_rating.toFixed(1)}
            </p>
          </div>
          <div>
            <p className="text-sm text-surface-500 dark:text-surface-400">Total reviews</p>
            <p className="mt-1 text-3xl font-bold">{profile.rating_count}</p>
          </div>
        </div>
      </div>

      <section className={`mt-6 ${CARD_STYLE}`}>
        <h2 className="text-lg font-semibold">Client reviews</h2>
        {items.length === 0 ? (
          <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
            No reviews yet. Reviews appear here once citizens rate your completed
            consultations.
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {items.map((review) => (
              <div key={review.id} className="border-t border-surface-200 pt-4 dark:border-surface-700">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">
                    {review.reviewer_name || 'Anonymous citizen'}
                  </span>
                  <span className="flex items-center gap-1 text-sm">
                    <Star className="h-4 w-4 fill-amber-400 text-amber-400" /> {review.rating}
                    {review.created_at && (
                      <span className="ml-2 text-surface-400">{fmtDate(review.created_at)}</span>
                    )}
                  </span>
                </div>
                {review.comment && (
                  <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
                    {review.comment}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
