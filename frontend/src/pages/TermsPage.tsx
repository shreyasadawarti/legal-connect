import { ReactNode } from 'react'
import { Link } from 'react-router-dom'

const sections: { heading: string; body: ReactNode[] }[] = [
  {
    heading: '1. What this is',
    body: [
      'Legal Connect is a college project: a directory and workflow platform for connecting people seeking legal help with lawyers. It is not a law firm, we are not a legal services provider, and we do not practise law.',
    ],
  },
  {
    heading: '2. No legal advice',
    body: [
      'Nothing on this platform — including the AI assistant — is legal advice. Do not act on it, and do not delay seeking advice because of it. AI output is generated text and can be wrong.',
    ],
  },
  {
    heading: '3. Not an emergency service',
    body: [
      'We do not provide 24-hour support, emergency response, or an on-call lawyer. If you are in danger, call 112 or the appropriate official helpline immediately.',
    ],
  },
  {
    heading: '4. No attorney–client relationship',
    body: [
      'Using the directory, requesting an appointment, or messaging a lawyer creates no relationship and no duty to you. Any engagement is between you and that lawyer, on their terms.',
    ],
  },
  {
    heading: '5. Payments',
    body: [
      'We do not process payments. No money moves through this platform. Any amount shown to a lawyer is their own estimate of confirmed and completed work, not income paid or received by us.',
    ],
  },
  {
    heading: '6. Verification is limited',
    body: [
      'We check that a submitted professional document exists and that an administrator approved the profile. We are not conducting an independent background check, and verification is not a guarantee of competence, availability, or outcome.',
    ],
  },
  {
    heading: '7. Reviews',
    body: [
      'Reviews come from users who report a completed appointment. We remove or refuse content that is abusive, defamatory, or fabricated, but we do not independently verify that every statement in a review is true.',
    ],
  },
  {
    heading: '8. Availability',
    body: [
      'Published availability is informational. A lawyer may decline any request, and accepting a request is not a guarantee that the appointment will take place.',
    ],
  },
  {
    heading: '9. Your account',
    body: [
      'You are responsible for keeping your credentials secure, and for telling us promptly if you suspect unauthorised access. We may suspend or deactivate accounts used unlawfully, to impersonate others, or to submit fraudulent reviews or verification documents.',
    ],
  },
  {
    heading: '10. Acceptable use',
    body: [
      'Do not post unlawful or abusive content, attempt to access other people’s accounts or documents, scrape or overload the service, misrepresent your identity, or use the platform to harass anyone.',
    ],
  },
  {
    heading: '11. Content you upload',
    body: [
      'You keep ownership of what you upload and confirm you have the right to share it. You are responsible for what you share and with whom, so use the sharing controls in the app.',
    ],
  },
  {
    heading: '12. Availability of features',
    body: [
      'AI features, video calls, and file hosting depend on third-party services being configured. Those features may be unavailable, and we will say so rather than simulate them.',
    ],
  },
  {
    heading: '13. Third-party links',
    body: [
      'Linked content and helpline numbers are provided for convenience. We are not responsible for third-party sites or services.',
    ],
  },
  {
    heading: '14. No warranty',
    body: [
      'The platform is provided as-is, without warranty of availability, accuracy, or fitness for a particular purpose.',
    ],
  },
  {
    heading: '15. Limitation of liability',
    body: [
      'To the fullest extent permitted by law, the project team is not liable for losses arising from use of, or inability to use, the platform.',
    ],
  },
  {
    heading: '16. Changes to these terms',
    body: [
      'These terms reflect the software as it currently stands and may change as the project develops.',
    ],
  },
]

export default function TermsPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          Terms of
          <span className="text-brand-600 dark:text-brand-400"> Service</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          The rules for using Legal Connect, written to match what the software actually does.
        </p>
      </div>

      <div className="mx-auto mt-12 max-w-3xl space-y-8">
        {sections.map((section) => (
          <div key={section.heading}>
            <h2 className="text-base font-bold">{section.heading}</h2>
            {section.body.map((paragraph, i) => (
              <p
                key={i}
                className="mt-2 text-sm leading-relaxed text-surface-600 dark:text-surface-300"
              >
                {paragraph}
              </p>
            ))}
          </div>
        ))}
      </div>

      <p className="mx-auto mt-10 max-w-3xl text-sm text-surface-600 dark:text-surface-300">
        We also describe what data we store and who can see it in our{' '}
        <Link to="/privacy" className="text-brand-600 hover:underline dark:text-brand-400">
          Privacy Policy
        </Link>
        .
      </p>

      <div className="mx-auto mt-14 max-w-3xl rounded-2xl bg-brand-700 p-8 text-center text-white">
        <h2 className="text-2xl font-bold">Questions about these terms?</h2>
        <p className="mt-2 text-brand-100">
          Read the FAQ first — it covers most of what people ask.
        </p>
        <Link
          to="/faq"
          className="mt-6 inline-flex rounded-lg bg-white px-6 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50"
        >
          Read the FAQ
        </Link>
      </div>
    </section>
  )
}