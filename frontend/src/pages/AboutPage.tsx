import { Link } from 'react-router-dom'
import { Brain, Check, FileText, MapPin, MessageSquare, Scale, Star, X } from 'lucide-react'

const built = [
  {
    icon: Scale,
    title: 'A structured lawyer directory',
    body: 'Twelve practice areas — family, criminal, civil, corporate, property, tax, labour, intellectual property, contract, personal injury, immigration, and general — searchable by name, practice area, city, and minimum rating, and shown on an interactive map.',
  },
  {
    icon: Check,
    title: 'A verification step that means something',
    body: 'Every professional profile must be reviewed by an administrator and backed by an uploaded document before it is approved. Administrators cannot approve a profile with no proof attached.',
  },
  {
    icon: CalendarIcon,
    title: 'A real appointment lifecycle',
    body: 'Clients request; lawyers accept or decline; work is marked complete; either side can cancel. Overlapping bookings for the same lawyer are blocked at the database level.',
  },
  {
    icon: MessageSquare,
    title: 'Real-time messaging and video',
    body: 'Direct one-to-one chat with typing indicators, read receipts, and unread counts, plus peer-to-peer video calling over WebRTC inside the same conversation.',
  },
  {
    icon: FileText,
    title: 'Private document handling',
    body: 'Uploads up to 25 MB, stored privately and delivered only through short-lived signed links. You choose who can open a file, and you can revoke that access whenever you like.',
  },
  {
    icon: Star,
    title: 'Reviews from real engagements',
    body: 'A rating can only be submitted for a completed appointment, once per client per lawyer. Ratings are recalculated automatically whenever a review is added or removed.',
  },
  {
    icon: Brain,
    title: 'AI assistance, clearly scoped',
    body: 'A legal assistant, a document summariser, a practice-area predictor, a legal-text translator, and a lawyer recommender. When the AI provider is not configured for a deployment, we say so rather than returning an invented answer.',
  },
  {
    icon: MapPin,
    title: 'Accountability',
    body: 'Clients file complaints and read the administrator’s response. Administrators act on suspended accounts, verifications, and complaints, with a record of who did what.',
  },
]

const notBuilt = [
  'There is no online payment processing. No money moves through this platform.',
  'There is no multilingual interface. A preferred language can be saved on your profile, but it does not currently change anything in the app.',
  'There is no 24/7 service and no on-call lawyer.',
  'We do not run background checks on lawyers. Verification confirms a document was submitted and approved, nothing more.',
]

function CalendarIcon(props: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  )
}

export default function AboutPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          About
          <span className="text-brand-600 dark:text-brand-400"> Legal Connect</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          Legal Connect exists to close one specific gap: finding a lawyer you can trust is hard.
        </p>
      </div>

      <div className="mx-auto mt-12 max-w-3xl space-y-4 text-base text-surface-600 dark:text-surface-300">
        <p>
          Ads are not recommendations. A name on a directory tells you nothing about whether that
          person practises in your area, speaks your language, or is even currently taking work.
          Legal Connect puts verified, structured, reviewable information in one place, and
          supports the rest of the engagement online.
        </p>
        <p>
          We are a college project, and we say so plainly. What follows is what we have actually
          built and what it actually does.
        </p>
      </div>

      <h2 className="mt-20 text-center text-2xl font-bold">What works today</h2>
      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        {built.map((item) => (
          <div
            key={item.title}
            className="rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800"
          >
            <item.icon className="h-7 w-7 text-brand-600" />
            <h3 className="mt-4 text-base font-semibold">{item.title}</h3>
            <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">{item.body}</p>
          </div>
        ))}
      </div>

      <h2 className="mt-20 text-center text-2xl font-bold">What we have not built</h2>
      <p className="mx-auto mt-3 max-w-2xl text-center text-sm text-surface-600 dark:text-surface-300">
        We do not advertise these, and you should not expect them.
      </p>
      <ul className="mx-auto mt-8 max-w-3xl space-y-3">
        {notBuilt.map((item) => (
          <li
            key={item}
            className="flex items-start gap-3 rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800"
          >
            <X className="mt-0.5 h-5 w-5 shrink-0 text-surface-400" />
            <span className="text-sm text-surface-600 dark:text-surface-300">{item}</span>
          </li>
        ))}
      </ul>

      <p className="mx-auto mt-10 max-w-3xl text-center text-sm text-surface-600 dark:text-surface-300">
        Where a feature depends on third-party configuration, we say so rather than simulate it. We
        would rather be useful and accurate than impressive and wrong.
      </p>

      <div className="mt-16 rounded-2xl bg-brand-700 p-8 text-center text-white">
        <h2 className="text-2xl font-bold">See it in action</h2>
        <p className="mt-2 text-brand-100">
          Create an account, or browse the directory without one.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/register"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50"
          >
            Create an account
          </Link>
          <Link
            to="/how-it-works"
            className="inline-flex items-center gap-2 rounded-lg border border-brand-500 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-800"
          >
            How it works
          </Link>
        </div>
      </div>
    </section>
  )
}