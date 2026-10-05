import { Link } from 'react-router-dom'
import { AlertTriangle, FileWarning, MessageCircle, Phone } from 'lucide-react'

const routes = [
  {
    icon: MessageCircle,
    title: 'For a legal matter',
    body: 'Please do not use this platform to ask for advice. Use the lawyer directory and speak to a qualified lawyer directly.',
    action: { label: 'Browse lawyers', to: '/lawyers' },
  },
  {
    icon: FileWarning,
    title: 'For a technical problem or wrong information',
    body: 'Report it through the in-app complaints section. You will see the administrator’s response there, which is the fastest route to a real answer.',
    action: null,
  },
  {
    icon: MessageCircle,
    title: 'For feedback on the project',
    body: 'Use the complaints section too. We read what comes through it.',
    action: null,
  },
  {
    icon: Phone,
    title: 'For anything urgent',
    body: 'Do not contact us. Call the relevant official helpline — 112 for general emergencies, or the numbers listed on the in-app Emergency Help page.',
    action: { label: 'How it works', to: '/how-it-works' },
  },
]

export default function ContactPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          Contact
          <span className="text-brand-600 dark:text-brand-400"> Us</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          We are a college project and there is no staffed support desk.
        </p>
      </div>

      <p className="mx-auto mt-8 max-w-3xl text-center text-base text-surface-600 dark:text-surface-300">
        Please use the channel that fits your issue. It is the fastest route to a real answer.
      </p>

      <div className="mx-auto mt-12 max-w-3xl space-y-4">
        {routes.map((route) => (
          <div
            key={route.title}
            className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800"
          >
            <div className="flex items-start gap-4">
              <route.icon className="mt-0.5 h-6 w-6 shrink-0 text-brand-600" />
              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold">{route.title}</h2>
                <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{route.body}</p>
                {route.action && (
                  <Link
                    to={route.action.to}
                    className="mt-4 inline-flex rounded-lg border border-surface-300 px-4 py-2 text-sm font-medium text-surface-800 hover:bg-surface-100 dark:border-surface-700 dark:text-surface-200 dark:hover:bg-surface-700"
                  >
                    {route.action.label}
                  </Link>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mx-auto mt-12 max-w-3xl rounded-2xl border border-amber-300 bg-amber-50 p-6 dark:border-amber-800 dark:bg-amber-950/30">
        <div className="flex items-start gap-4">
          <AlertTriangle className="mt-0.5 h-6 w-6 shrink-0 text-amber-600" />
          <div>
            <h2 className="text-base font-semibold text-amber-900 dark:text-amber-200">
              No email address or phone number is published here
            </h2>
            <p className="mt-2 text-sm text-amber-800 dark:text-amber-300">
              Not because we are hiding one, but because none is monitored. Publishing contact
              details nobody checks would waste your time more than an empty page does. The
              complaints section is the only channel we can actually see and answer.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}