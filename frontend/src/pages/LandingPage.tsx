import { Link } from 'react-router-dom'
import { ArrowRight, FileText, Scale, Video } from 'lucide-react'

export default function LandingPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          Legal Assistance,
          <span className="text-brand-600 dark:text-brand-400"> Simplified.</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          Connect with verified lawyers, chat securely, upload documents, and get AI-powered legal
          guidance — all in one place.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/lawyers"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Find a Lawyer
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 rounded-lg border border-surface-300 px-6 py-3 text-sm font-semibold text-surface-800 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-200 dark:hover:bg-surface-800"
          >
            Get Started
          </Link>
        </div>
      </div>

      <div className="mt-20 grid gap-6 sm:grid-cols-3">
        <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
          <Scale className="h-8 w-8 text-brand-600" />
          <h3 className="mt-4 text-lg font-semibold">Verified Lawyers</h3>
          <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
            Browse vetted legal professionals across multiple practice areas.
          </p>
        </div>
        <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
          <Video className="h-8 w-8 text-brand-600" />
          <h3 className="mt-4 text-lg font-semibold">Video Consultations</h3>
          <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
            Meet your lawyer securely through built-in video consultations.
          </p>
        </div>
        <div className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
          <FileText className="h-8 w-8 text-brand-600" />
          <h3 className="mt-4 text-lg font-semibold">Secure Documents</h3>
          <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
            Upload and share legal documents privately with advanced security.
          </p>
        </div>
      </div>

      <div className="mt-16 rounded-2xl bg-brand-700 p-8 text-center text-white">
        <h2 className="text-2xl font-bold">Need legal help now?</h2>
        <p className="mt-2 text-brand-100">
          Our AI assistant can help you understand your legal situation around the clock.
        </p>
        <Link
          to="/login"
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50"
        >
          Try AI Assistant
        </Link>
      </div>
    </section>
  )
}
