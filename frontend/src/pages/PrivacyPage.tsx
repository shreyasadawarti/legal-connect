import { Link } from 'react-router-dom'

const collected: { heading: string; items: string[] }[] = [
  {
    heading: 'Account data',
    items: [
      'Your name, email address, hashed password, phone number, city, residential address, a short bio, and your preferred language. Your preferred language is stored but does not currently change anything in the interface.',
      'Your role and account status, and the time you last signed in.',
    ],
  },
  {
    heading: 'Professional data, for lawyers',
    items: [
      'Practice areas, specializations, languages spoken, years of experience, hourly rate, weekly availability, city and map coordinates.',
      'Your uploaded verification document.',
    ],
  },
  {
    heading: 'Activity data',
    items: [
      'Appointments: requested times, duration, category, and the description you enter.',
      'Messages: conversation content between you and the person you are messaging.',
      'Documents: the files you upload, their metadata, and who you have shared them with.',
      'Reviews: your star rating, comment, and any lawyer reply.',
      'Operational records: notifications, complaint text and responses, and an administrative audit log of sensitive actions such as verification decisions, account status changes, and document sharing.',
    ],
  },
]

const visibility: { heading: string; items: string[] }[] = [
  {
    heading: 'Who can see what',
    items: [
      'Your account details and appointment history: you.',
      'An appointment: you and the lawyer involved.',
      'Messages: you and the person you are messaging.',
      'Documents: you, and anyone you explicitly share with. A lawyer’s verification document is visible to that lawyer and to the administrators reviewing it.',
      'Reviews: public, attributed to your first name and last initial.',
      'Complaint text: you, administrators, and anyone the complaint concerns.',
    ],
  },
]

export default function PrivacyPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          Privacy
          <span className="text-brand-600 dark:text-brand-400"> Policy</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          What we store, who can see it, and what we cannot offer you.
        </p>
      </div>

      <div className="mx-auto mt-12 max-w-3xl rounded-2xl border border-surface-200 bg-white p-6 dark:border-surface-800 dark:bg-surface-800">
        <p className="text-sm text-surface-600 dark:text-surface-300">
          <span className="font-semibold">Scope.</span> This policy describes the Legal Connect
          college project. It is not a certified, audited privacy programme, and we are not making
          compliance claims.
        </p>
      </div>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">What we collect</h2>
      <div className="mx-auto mt-6 max-w-3xl space-y-6">
        {collected.map((group) => (
          <div key={group.heading}>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
              {group.heading}
            </h3>
            <ul className="mt-3 space-y-2">
              {group.items.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-sm text-surface-600 dark:text-surface-300"
                >
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">Where it lives</h2>
      <p className="mx-auto mt-4 max-w-3xl text-sm text-surface-600 dark:text-surface-300">
        Account and activity data is stored in a MySQL database. Uploaded documents are stored with
        an online file-hosting provider; the database holds only a reference to each file, not its
        contents.
      </p>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">Visibility</h2>
      <div className="mx-auto mt-6 max-w-3xl space-y-6">
        {visibility.map((group) => (
          <div key={group.heading}>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
              {group.heading}
            </h3>
            <ul className="mt-3 space-y-2">
              {group.items.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-sm text-surface-600 dark:text-surface-300"
                >
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">
        Sessions and authentication data
      </h2>
      <p className="mx-auto mt-4 max-w-3xl text-sm text-surface-600 dark:text-surface-300">
        Access and refresh tokens are held in your browser&apos;s local storage so you stay signed in
        between visits. Signing out clears them locally. Password reset and verification tokens are
        time-limited. Passwords are hashed with bcrypt and are never stored or emailed in plain
        text.
      </p>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">Third parties</h2>
      <p className="mx-auto mt-4 max-w-3xl text-sm text-surface-600 dark:text-surface-300">
        If AI features are enabled, text you submit to them is sent to the configured AI provider to
        generate a response. We do not send your documents, messages, or identity documents to the
        AI provider. We use no advertising, analytics, or social tracking services, and we set no
        tracking cookies — there is nothing to consent to.
      </p>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">What you should know</h2>
      <ul className="mx-auto mt-6 max-w-3xl space-y-2">
        {[
          'We cannot offer end-to-end confidentiality once information is typed into a form. Files are stored by a third-party hosting provider, and any AI feature you use sends your text to an AI provider.',
          'Video calls connect directly between the two participants’ browsers.',
          'Sharing is single-recipient at a time. If you share a file with the wrong account, remove that access immediately.',
          'Email delivery for verification and password reset depends on configuration. Where it is unavailable, those emails are not sent at all, so do not rely on them to recover an account.',
        ].map((item) => (
          <li
            key={item}
            className="flex items-start gap-3 text-sm text-surface-600 dark:text-surface-300"
          >
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />
            <span>{item}</span>
          </li>
        ))}
      </ul>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">Your choices</h2>
      <p className="mx-auto mt-4 max-w-3xl text-sm text-surface-600 dark:text-surface-300">
        You can update your name, phone, city, address, bio, and preferred language from your
        profile page at any time. You can revoke document sharing, delete documents, delete your own
        review, and file a complaint about data handling, all from within the app. Full account
        deletion is not currently self-service — please raise it through the complaints section.
      </p>

      <h2 className="mx-auto mt-14 max-w-3xl text-2xl font-bold">Changes to this policy</h2>
      <p className="mx-auto mt-4 max-w-3xl text-sm text-surface-600 dark:text-surface-300">
        Because this is an active student project, this policy reflects the code as it stands today
        rather than making a permanent commitment. See also our{' '}
        <Link to="/terms" className="text-brand-600 hover:underline dark:text-brand-400">
          Terms of Service
        </Link>
        .
      </p>
    </section>
  )
}