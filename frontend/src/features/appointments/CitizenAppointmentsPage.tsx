import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, CheckCircle2, Loader2, Star, Video, Wallet } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { openRazorpayCheckout } from '@/lib/razorpay'
import { cancelAppointment, listAppointments } from '@/services/appointmentService'
import { createPaymentOrder, getAppointmentPayment, verifyPayment } from '@/services/paymentService'
import { submitReview } from '@/services/socialService'
import type { Appointment } from '@/types/platform'

import VideoCallLink from './VideoCallLink'

const STATUS_COLOR: Record<string, string> = {
  PENDING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  CONFIRMED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  CANCELLED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  REJECTED: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  NO_SHOW: 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300',
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const PAYABLE_STATUSES = new Set(['CONFIRMED', 'COMPLETED'])

function PayButton({ appointment }: { appointment: Appointment }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState('')

  const { data: payment, isLoading } = useQuery({
    queryKey: ['appointment-payment', appointment.id],
    queryFn: () => getAppointmentPayment(appointment.id),
  })

  const payMut = useMutation({
    mutationFn: async () => {
      const order = await createPaymentOrder(appointment.id)
      const checkout = await openRazorpayCheckout({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        order_id: order.order_id,
        name: 'Legal Connect',
        description: order.description,
      })
      return verifyPayment({
        payment_id: order.payment_id,
        razorpay_order_id: checkout.razorpay_order_id,
        razorpay_payment_id: checkout.razorpay_payment_id,
        razorpay_signature: checkout.razorpay_signature,
      })
    },
    onSuccess: () => {
      setError('')
      queryClient.invalidateQueries({ queryKey: ['appointment-payment', appointment.id] })
    },
    onError: (err) => {
      const message = (err as Error)?.message
      if (message === 'PAYMENT_CANCELLED') return
      if (message === 'PAYMENT_FAILED') {
        setError('Payment failed. Please try again.')
        return
      }
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || message || 'Could not start the payment. Please try again.')
    },
  })

  if (isLoading) return null

  if (payment?.status === 'PAID') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-lg bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">
        <CheckCircle2 className="h-4 w-4" /> Paid
      </span>
    )
  }

  if (!PAYABLE_STATUSES.has(appointment.status)) return null

  return (
    <span className="inline-flex flex-col gap-1">
      <button
        onClick={() => {
          setError('')
          payMut.mutate()
        }}
        disabled={payMut.isPending}
        className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
      >
        <Wallet className="h-4 w-4" />
        {payMut.isPending ? 'Processing…' : 'Pay consultation fee'}
      </button>
      {error && <span className="text-xs text-red-600 dark:text-red-400">{error}</span>}
    </span>
  )
}

function AppointmentCard({ appointment }: { appointment: Appointment }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [reviewMode, setReviewMode] = useState(false)
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [reviewError, setReviewError] = useState('')
  const [justReviewed, setJustReviewed] = useState(false)

  const isCompleted = appointment.status === 'COMPLETED'

  // The appointment carries its own reviewed flag, so a review is scoped to the
  // exact appointment rather than the lawyer. justReviewed flips it immediately
  // on submit instead of waiting for the refetch.
  const hasReviewed = justReviewed || Boolean(appointment.reviewed)
  const canSubmit = comment.trim().length > 0

  const cancelMut = useMutation({
    mutationFn: () => cancelAppointment(appointment.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['appointments'] }),
  })
  const reviewMut = useMutation({
    mutationFn: () => submitReview(appointment.lawyer_id, rating, comment, appointment.id),
    onSuccess: () => {
      setReviewMode(false)
      setReviewError('')
      setComment('')
      setJustReviewed(true)
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['lawyer-reviews'] })
    },
    onError: (error) => {
      const status = (error as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        // Already reviewed from another session or tab.
        setReviewMode(false)
        setReviewError('')
        setJustReviewed(true)
        queryClient.invalidateQueries({ queryKey: ['appointments'] })
      } else {
        setReviewError('Could not submit your review. Please try again.')
      }
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <div className="flex items-center justify-between gap-3">
        <h3 className="min-w-0 truncate font-semibold">{appointment.lawyer_name}</h3>
        <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[appointment.status] ?? ''}`}>
          {appointment.status}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-sm text-surface-500 dark:text-surface-400">
        <Calendar className="h-4 w-4" />
        {fmtDate(appointment.start_time)} – {fmtDate(appointment.end_time)}
      </div>
      <div className="mt-1 text-sm text-surface-500 dark:text-surface-400">{appointment.category.replace('_', ' ')}</div>

      <div className="mt-4 flex flex-wrap gap-2">
        {appointment.status === 'CONFIRMED' && (
          <button
            onClick={() => navigate(`/video-call/${appointment.id}`)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            <Video className="h-4 w-4" /> Video call
          </button>
        )}
        {(appointment.status === 'PENDING' || appointment.status === 'CONFIRMED') && (
          <button
            onClick={() => cancelMut.mutate()}
            disabled={cancelMut.isPending}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-60 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
          >
            {cancelMut.isPending ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
        {isCompleted && !reviewMode && hasReviewed && (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-green-100 px-3 py-1.5 text-sm font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" /> Review Done
          </span>
        )}
        {isCompleted && !reviewMode && !hasReviewed && (
          <button
            onClick={() => setReviewMode(true)}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Leave a review
          </button>
        )}
        <PayButton appointment={appointment} />
      </div>

      {appointment.status === 'CONFIRMED' && <VideoCallLink appointment={appointment} />}

      {reviewMode && (
        <form
          noValidate
          className="mt-4 space-y-3 rounded-xl bg-surface-50 p-4 dark:bg-surface-900"
          onSubmit={(e) => {
            e.preventDefault()
            setReviewError('')
            reviewMut.mutate()
          }}
        >
          {(reviewError || reviewMut.isError) && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {reviewError || 'Could not submit your review. Please try again.'}
            </p>
          )}
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                className="text-xl"
                aria-label={`${n} star`}
              >
                <Star className={`h-6 w-6 ${n <= rating ? 'fill-amber-400 text-amber-400' : 'text-surface-300'}`} />
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            required
            placeholder="Share your experience with this lawyer"
            className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={reviewMut.isPending || !canSubmit}
              className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {reviewMut.isPending ? 'Submitting…' : 'Submit review'}
            </button>
            <button
              type="button"
              onClick={() => setReviewMode(false)}
              className="rounded-lg border border-surface-300 px-4 py-1.5 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

export default function CitizenAppointmentsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['appointments'],
    queryFn: () => listAppointments(),
    // A lawyer completing a booking happens in another session, so always
    // refetch on entry and on focus to surface the "Leave a review" button.
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold">My appointments</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Manage your consultations and leave reviews after they complete.
      </p>

      {isLoading && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
        </div>
      )}
      {isError && (
        <p className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Could not load appointments.
        </p>
      )}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <p className="mt-8 rounded-lg bg-surface-100 px-4 py-6 text-center text-sm text-surface-500 dark:bg-surface-800 dark:text-surface-400">
          You have no appointments yet.
        </p>
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="mt-6 space-y-4">
          {data.items.map((appointment) => (
            <AppointmentCard key={appointment.id} appointment={appointment} />
          ))}
        </div>
      )}
    </div>
  )
}
