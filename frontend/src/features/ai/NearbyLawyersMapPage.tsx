import { useQuery } from '@tanstack/react-query'
import { LocateFixed, Loader2, MapPin } from 'lucide-react'
import { useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import { aiNearbyLawyers } from '@/services/aiService'
import type { LawyerProfile } from '@/types/platform'

// Fix default marker icons that break under bundlers.
const defaultIcon = L.icon({
  iconUrl:
    'data:image/svg+xml;base64,' +
    btoa(
      '<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41"><path fill="#4f46e5" stroke="#312e81" stroke-width="1" d="M12.5 0C5.6 0 0 5.6 0 12.5 0 21 9.6 34 12.5 41c2.9-7 12.5-20 12.5-28.5C25 5.6 19.4 0 12.5 0z"/><circle cx="12.5" cy="12.5" r="5.5" fill="#fff"/></svg>',
    ),
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [0, -41],
})
L.Marker.prototype.options.icon = defaultIcon

const DEFAULT_CENTER: [number, number] = [20.5937, 78.9629] // India

function fmtRate(rate: number) {
  if (!rate) return 'Rate not set'
  return `₹${rate}/hr`
}

function MapView({ lawyers }: { lawyers: LawyerProfile[] }) {
  const [center, setCenter] = useState<[number, number]>(DEFAULT_CENTER)
  const [zoom, setZoom] = useState(5)
  const [locating, setLocating] = useState(false)

  const locate = () => {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCenter([pos.coords.latitude, pos.coords.longitude])
        setZoom(11)
        setLocating(false)
      },
      () => setLocating(false),
      { timeout: 10000 },
    )
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-surface-500 dark:text-surface-400">
          Showing {lawyers.length} lawyer{lawyers.length === 1 ? '' : 's'} with a location on the map.
        </p>
        <button
          type="button"
          onClick={locate}
          disabled={locating}
          className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 px-3 py-1.5 text-sm hover:bg-surface-100 disabled:opacity-60 dark:border-surface-700 dark:hover:bg-surface-700"
        >
          {locating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <LocateFixed className="h-4 w-4" />
          )}
          Use my location
        </button>
      </div>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '28rem', width: '100%', borderRadius: '1rem' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {lawyers.map((l) =>
          typeof l.latitude === 'number' && typeof l.longitude === 'number' ? (
            <Marker key={l.user_id} position={[l.latitude, l.longitude]}>
              <Popup>
                <strong>{l.name}</strong>
                <br />
                <span>{l.city || '—'}</span>
                <br />
                <span>{fmtRate(l.hourly_rate)}</span>
                <br />
                <span className="text-brand-600">
                  {'★'.repeat(Math.round(l.avg_rating))}
                  {l.avg_rating > 0 ? ` ${l.avg_rating.toFixed(1)}` : 'No ratings yet'}
                </span>
              </Popup>
            </Marker>
          ) : null,
        )}
      </MapContainer>
    </div>
  )
}

export default function NearbyLawyersMapPage() {
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ['nearby-lawyers'],
    queryFn: () => aiNearbyLawyers({}),
  })

  const lawyers = data?.items ?? []

  return (
    <div>
      <h1 className="flex items-center gap-2 text-2xl font-bold">
        <MapPin className="h-7 w-7 text-brand-600" /> Nearby Lawyers
      </h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Explore verified lawyers on an OpenStreetMap map. Turn on location to see those near you.
      </p>

      <div className="mt-5">
        {isLoading && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          </div>
        )}
        {isError && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/30 dark:text-red-300">
            <p className="font-semibold">Could not load the map.</p>
            <p>No lawyers with a location are available yet, or the network failed.</p>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isRefetching}
              className="mt-3 rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
            >
              {isRefetching ? 'Retrying…' : 'Retry'}
            </button>
          </div>
        )}
        {!isLoading && !isError && lawyers.length === 0 && (
          <div className="rounded-2xl border border-surface-200 bg-surface-50 p-6 text-sm text-surface-500 dark:border-surface-800 dark:bg-surface-800 dark:text-surface-400">
            No lawyers on the map yet. Lawyers appear here once they add their location to their
            profile.
          </div>
        )}
        {!isLoading && !isError && lawyers.length > 0 && <MapView lawyers={lawyers} />}
      </div>
    </div>
  )
}
