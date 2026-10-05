import { MapPin, Phone } from 'lucide-react'
import { Link } from 'react-router-dom'

const HELPLINES = [
  {
    name: 'National Emergency',
    number: '112',
    description: 'Police, fire, ambulance — all-India emergency number',
  },
  {
    name: 'Police',
    number: '100',
    description: 'Report crimes or request police assistance',
  },
  {
    name: 'Women Helpline',
    number: '1091',
    description: '24/7 helpline for women in distress',
  },
  {
    name: 'Child Helpline',
    number: '1098',
    description: 'Support for children in need of care and protection',
  },
  {
    name: 'Senior Citizens Helpline',
    number: '14567',
    description: 'Assistance for senior citizens',
  },
  {
    name: 'National Legal Services Authority (NALSA)',
    number: '15100',
    description: 'Free legal aid helpline for eligible persons',
  },
  {
    name: 'Cyber Crime Helpline',
    number: '1930',
    description: 'Report online fraud and cyber crime',
  },
  {
    name: 'National Emergency (Disaster)',
    number: '1078',
    description: 'Disaster management and relief assistance',
  },
]

export default function EmergencyHelpPage() {
  return (
    <div>
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-900/20">
        <h1 className="text-2xl font-bold text-red-800 dark:text-red-200">
          Emergency Legal Help
        </h1>
        <p className="mt-1 text-sm text-red-700 dark:text-red-300">
          If you are in immediate danger, call the emergency number (112) right away. Use the
          helplines below for legal and support assistance.
        </p>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {HELPLINES.map((h) => (
          <div
            key={h.name}
            className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800"
          >
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold">{h.name}</h3>
              <Phone className="h-4 w-4 text-brand-600" />
            </div>
            <a
              href={`tel:${h.number}`}
              className="mt-2 inline-block text-2xl font-bold text-brand-700 dark:text-brand-400"
            >
              {h.number}
            </a>
            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">{h.description}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50 p-6 dark:border-brand-900 dark:bg-brand-900/20">
        <h2 className="text-lg font-semibold text-brand-800 dark:text-brand-200">
          Find a lawyer nearby
        </h2>
        <p className="mt-1 text-sm text-brand-700 dark:text-brand-300">
          For non-urgent legal matters, locate verified lawyers close to you.
        </p>
        <Link
          to="/nearby-lawyers"
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          <MapPin className="h-4 w-4" />
          Browse nearby lawyers
        </Link>
      </div>
    </div>
  )
}
