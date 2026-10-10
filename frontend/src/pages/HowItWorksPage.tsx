import { Link } from 'react-router-dom'
import { CalendarCheck, MessageSquare, Search, ShieldCheck, Upload, Video } from 'lucide-react'

const clientSteps = [
  {
    icon: Search,
    title: 'Find a lawyer',
    body: 'Search the directory by name, practice area, city, or minimum rating, or browse the map. Each listing shows practice areas, years of experience, hourly rate, the languages they work in, and reviews from people who have actually met with them.',
  },
  {
    icon: CalendarCheck,
    title: 'Request an appointment',
    body: 'Pick a time, describe what you need, and send the request. The lawyer can accept it, decline it, or ask for more detail. Appointments move through clear stages — pending, confirmed, completed, cancelled, or declined — so you always know where things stand.',
  },
  {
    icon: MessageSquare,
    title: 'Talk it through',
    body: 'Once an appointment is confirmed, message your lawyer in real time with typing indicators and read receipts. Share case documents from your documents area — you choose who can open them, and you can revoke access at any time.',
  },
]

const lawyerSteps = [
  {
    icon: ShieldCheck,
    title: 'Get verified',
    body: 'Create a professional profile with your practice areas, languages, hourly rate, and weekly availability, then upload documentary proof. An administrator reviews it before your profile is listed publicly.',
  },
  {
    icon: CalendarCheck,
    title: 'Manage requests',
    body: 'Accept or decline incoming appointment requests, keep your appointment history, and see an estimate of what your confirmed and completed work adds up to.',
  },
]

export default function HowItWorksPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          How It
          <span className="text-brand-600 dark:text-brand-400"> Works</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          Three steps for people seeking legal help, two for lawyers. No guesswork at any stage.
        </p>
      </div>

      <h2 className="mt-20 text-center text-2xl font-bold">If you need a lawyer</h2>
      <div className="mt-8 grid gap-6 sm:grid-cols-3">
        {clientSteps.map((step, i) => (
          <div
            key={step.title}
            className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800"
          >
            <step.icon className="h-8 w-8 text-brand-600" />
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
              Step {i + 1}
            </p>
            <h3 className="mt-1 text-lg font-semibold">{step.title}</h3>
            <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{step.body}</p>
          </div>
        ))}
      </div>

      <h2 className="mt-20 text-center text-2xl font-bold">If you are a lawyer</h2>
      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        {lawyerSteps.map((step, i) => (
          <div
            key={step.title}
            className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800"
          >
            <step.icon className="h-8 w-8 text-brand-600" />
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
              Step {i + 1}
            </p>
            <h3 className="mt-1 text-lg font-semibold">{step.title}</h3>
            <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{step.body}</p>
          </div>
        ))}
      </div>

      <div className="mt-16 grid gap-6 sm:grid-cols-3">
        <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
          <Video className="h-8 w-8 text-brand-600" />
          <h3 className="mt-4 text-lg font-semibold">Video calls</h3>
          <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
            Once an appointment is confirmed, start a peer-to-peer video call inside the chat
            window. Both of you need a camera, microphone, and a network that permits direct
            connections.
          </p>
        </div>
        <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
          <Upload className="h-8 w-8 text-brand-600" />
          <h3 className="mt-4 text-lg font-semibold">Documents</h3>
          <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
            Upload files up to 25 MB. They are stored privately and only reachable through
            short-lived signed links. Lawyer verification documents must be a PDF, PNG, or JPG.
          </p>
        </div>
        <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
          <ShieldCheck className="h-8 w-8 text-brand-600" />
          <h3 className="mt-4 text-lg font-semibold">Accountability</h3>
          <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
            File a complaint and read the administrator&apos;s response. Administrators record
            verification decisions, status changes, and document sharing in an audit log.
          </p>
        </div>
      </div>

      <div className="mt-16 rounded-2xl bg-brand-700 p-6 text-center text-white sm:p-8">
        <h2 className="text-2xl font-bold">Ready to begin?</h2>
        <p className="mt-2 text-brand-100">Create an account, or browse the directory first.</p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/register"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50"
          >
            Create an account
          </Link>
          <Link
            to="/lawyers"
            className="inline-flex items-center gap-2 rounded-lg border border-brand-500 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-800"
          >
            Browse lawyers
          </Link>
        </div>
      </div>
    </section>
  )
}