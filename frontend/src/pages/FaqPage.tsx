import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'

interface Faq {
  question: string
  answer: string
}

const groups: { heading: string; items: Faq[] }[] = [
  {
    heading: 'About the service',
    items: [
      {
        question: 'What is Legal Connect?',
        answer:
          'A directory and workflow platform that connects people who need legal help with lawyers, and supports the appointment, messaging, document, and review process around it. It is a college project built on FastAPI, MySQL, and React.',
      },
      {
        question: 'Are the lawyers verified?',
        answer:
          'A professional profile must be reviewed by an administrator and backed by an uploaded document — a PDF, PNG, or JPG — before it is approved. Unapproved profiles are not publicly listed and cannot be booked. This confirms a document was submitted and approved; it is not a background check.',
      },
    ],
  },
  {
    heading: 'Finding a lawyer',
    items: [
      {
        question: 'How do I search?',
        answer:
          'By name or keyword, practice area, city, and minimum rating. You can also browse the map. Twelve practice areas are covered: family, criminal, civil, corporate, property, tax, labour, intellectual property, contract, personal injury, immigration, and general.',
      },
      {
        question: 'How do ratings and reviews work?',
        answer:
          'Only a client with a completed appointment can review that lawyer, once per lawyer. Ratings are recalculated automatically whenever a review is added or removed, so the average you see is never stale.',
      },
    ],
  },
  {
    heading: 'Appointments',
    items: [
      {
        question: 'How do I book, and can I cancel?',
        answer:
          'Send a request with a preferred time and a short description of what you need. The lawyer can accept or decline it. Either of you can cancel while an appointment is pending or confirmed. If you need a different time, contact your lawyer to agree on one — the system tracks the booking but you arrange the change together.',
      },
      {
        question: 'Is a lawyer’s availability guaranteed?',
        answer:
          'No. Lawyers publish their weekly working hours so you can see roughly when they work, but a lawyer may still decline any request. Accepting a request is not a guarantee that the appointment will go ahead.',
      },
    ],
  },
  {
    heading: 'Messaging and documents',
    items: [
      {
        question: 'Can I upload documents?',
        answer:
          'Yes. Uploads are limited to 25 MB. Files are stored privately and are never served as public links — they are only reachable through time-limited signed links. You choose who can open a file, one recipient at a time, and you can revoke that access whenever you like. Lawyer verification documents must be a PDF, PNG, or JPG. Note that we cannot offer end-to-end confidentiality once a file is uploaded, because storage is handled by a third-party hosting provider.',
      },
      {
        question: 'Is chat and video calling real-time?',
        answer:
          'Yes. Chat is live, with typing indicators, read receipts, and unread counts. Video is peer-to-peer in your browser using WebRTC, inside the chat window. Both people need a camera, microphone, and a network that permits direct connections — restrictive corporate or mobile networks may block the call.',
      },
    ],
  },
  {
    heading: 'Payments, AI, and safety',
    items: [
      {
        question: 'Can I pay through Legal Connect?',
        answer:
          'No. We do not process payments and no money moves through this platform. Any figures shown to a lawyer are an estimate of their own confirmed and completed work, not income received.',
      },
      {
        question: 'Is the AI assistant always available?',
        answer:
          'No. The assistant answers legal questions, summarises documents you paste, predicts which practice area fits a situation, translates legal text, and suggests lawyers — all of which depend on an external AI provider being configured for the deployment. When it is not, we tell you plainly instead of returning an invented answer. Nothing it produces is legal advice.',
      },
      {
        question: 'How do I raise a problem?',
        answer:
          'Use the complaints section. Your complaint and the administrator’s response are both visible to you. If you need urgent help, do not contact us — call 112 for general emergencies, or the official helplines listed on the in-app Emergency Help page. Legal Connect is not an emergency or 24-hour service.',
      },
    ],
  },
]

export default function FaqPage() {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
          Frequently Asked
          <span className="text-brand-600 dark:text-brand-400"> Questions</span>
        </h1>
        <p className="mt-6 text-lg text-surface-600 dark:text-surface-300">
          Straight answers, including where the answer is no.
        </p>
      </div>

      <div className="mx-auto mt-14 max-w-3xl space-y-10">
        {groups.map((group) => (
          <div key={group.heading}>
            <h2 className="text-lg font-bold">{group.heading}</h2>
            <div className="mt-4 space-y-3">
              {group.items.map((faq) => {
                const isOpen = open === faq.question
                return (
                  <div
                    key={faq.question}
                    className="overflow-hidden rounded-2xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800"
                  >
                    <button
                      onClick={() => setOpen(isOpen ? null : faq.question)}
                      aria-expanded={isOpen}
                      className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                    >
                      <span className="text-sm font-semibold">{faq.question}</span>
                      <ChevronDown
                        className={`h-4 w-4 shrink-0 text-surface-500 transition-transform ${
                          isOpen ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                    {isOpen && (
                      <p className="px-5 pb-5 text-sm text-surface-600 dark:text-surface-300">
                        {faq.answer}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mx-auto mt-14 max-w-3xl rounded-2xl bg-brand-700 p-8 text-center text-white">
        <h2 className="text-2xl font-bold">Still have a question?</h2>
        <p className="mt-2 text-brand-100">
          Read how the platform works, or send a request through the directory.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/how-it-works"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50"
          >
            How it works
          </Link>
          <Link
            to="/contact"
            className="inline-flex items-center gap-2 rounded-lg border border-brand-500 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-800"
          >
            Contact
          </Link>
        </div>
      </div>
    </section>
  )
}