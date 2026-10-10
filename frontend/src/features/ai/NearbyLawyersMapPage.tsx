import { useQuery } from '@tanstack/react-query'
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  LocateFixed,
  MapPin,
  Navigation,
  Search,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
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

const RADIUS_OPTIONS: { label: string; value: number | undefined }[] = [
  { label: 'Any distance', value: undefined },
  { label: 'Within 5 km', value: 5 },
  { label: 'Within 10 km', value: 10 },
  { label: 'Within 25 km', value: 25 },
  { label: 'Within 50 km', value: 50 },
  { label: 'Within 100 km', value: 100 },
]

type GeoStatus = 'idle' | 'locating' | 'granted' | 'denied' | 'unavailable'

interface Coords {
  lat: number
  lng: number
}

function isUsable(lawyer: LawyerProfile): boolean {
  const { latitude, longitude } = lawyer
  return (
    typeof latitude === 'number' &&
    typeof longitude === 'number' &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  )
}

function formatRate(rate: number) {
  return rate ? `₹${rate}/hr` : 'Rate not set'
}

function formatDistance(km?: number) {
  if (typeof km !== 'number') return null
  if (km < 1) return `${Math.round(km * 1000)} m away`
  return `${km.toFixed(1)} km away`
}

function specializationsOf(lawyer: LawyerProfile) {
  if (lawyer.specializations?.length) return lawyer.specializations.join(', ')
  return (lawyer.categories ?? []).map((c) => c.replace(/_/g, ' ')).join(', ')
}

function MapFocus({ center }: { center: [number, number] }) {
  const map = useMap()
  useEffect(() => {
    map.setView(center, 11)
  }, [map, center])
  return null
}

function MapView({
  lawyers,
  center,
  focusOnUser,
}: {
  lawyers: LawyerProfile[]
  center: [number, number]
  focusOnUser: boolean
}) {
  return (
    <MapContainer
      center={center}
      zoom={focusOnUser ? 11 : 5}
      style={{ height: 'min(60vh, 26rem)', width: '100%', borderRadius: '1rem' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {focusOnUser && <MapFocus center={center} />}
      {lawyers.map((l) => (
        <Marker key={l.user_id} position={[l.latitude as number, l.longitude as number]}>
          <Popup>
            <strong>{l.name}</strong>
            <br />
            <span>{specializationsOf(l) || '—'}</span>
            <br />
            <span>{l.city || '—'}</span>
            <br />
            <span>{formatRate(l.hourly_rate)}</span>
            {typeof l.distance_km === 'number' && (
              <>
                <br />
                <span>{formatDistance(l.distance_km)}</span>
              </>
            )}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}

export default function NearbyLawyersMapPage() {
  const [coords, setCoords] = useState<Coords | null>(null)
  const [geoStatus, setGeoStatus] = useState<GeoStatus>('idle')
  const [radiusKm, setRadiusKm] = useState<number | undefined>(undefined)
  const [sort, setSort] = useState<'distance' | 'rating'>('distance')

  const effectiveSort = coords ? sort : 'rating'

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: [
      'nearby-lawyers',
      coords?.lat ?? null,
      coords?.lng ?? null,
      radiusKm ?? null,
      effectiveSort,
    ],
    queryFn: () =>
      aiNearbyLawyers({
        lat: coords?.lat,
        lng: coords?.lng,
        radius_km: radiusKm,
        sort: effectiveSort,
      }),
  })

  const lawyers = (data?.items ?? []).filter(isUsable)
  const center: [number, number] = coords ? [coords.lat, coords.lng] : DEFAULT_CENTER

  const requestLocation = () => {
    if (!('geolocation' in navigator)) {
      setGeoStatus('unavailable')
      return
    }
    setGeoStatus('locating')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({ lat: position.coords.latitude, lng: position.coords.longitude })
        setGeoStatus('granted')
      },
      (error) => {
        setGeoStatus(
          error.code === error.PERMISSION_DENIED ? 'denied' : 'unavailable',
        )
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    )
  }

  return (
    <div>
      <h1 className="flex items-center gap-2 text-2xl font-bold">
        <MapPin className="h-7 w-7 text-brand-600" /> Nearby Lawyers
      </h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Share your location once to find verified lawyers closest to you, then sort by distance or
        filter by how far you are willing to travel.
      </p>

      {/* Location permission prompt */}
      <div className="mt-5 rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium">Find lawyers near your current location</p>
            <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
              We ask your browser for permission first. Your precise location is only used for this
              search and is never stored.
            </p>
          </div>
          <button
            type="button"
            onClick={requestLocation}
            disabled={geoStatus === 'locating'}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {geoStatus === 'locating' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LocateFixed className="h-4 w-4" />
            )}
            {geoStatus === 'locating' ? 'Locating…' : 'Find Nearby Lawyers'}
          </button>
        </div>

        {geoStatus === 'granted' && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" /> Location shared. Results are sorted by distance.
          </p>
        )}
        {(geoStatus === 'denied' || geoStatus === 'unavailable') && (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 dark:border-amber-900 dark:bg-amber-900/30 dark:text-amber-300">
            <p className="inline-flex items-center gap-1.5 font-medium">
              <AlertCircle className="h-4 w-4" />
              {geoStatus === 'denied'
                ? 'Location permission was denied.'
                : 'We could not determine your location.'}
            </p>
            <p className="mt-1">
              You can still browse and search lawyers manually.
            </p>
            <Link
              to="/lawyers"
              className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 font-semibold text-white hover:bg-amber-700"
            >
              <Search className="h-4 w-4" /> Search lawyers manually
            </Link>
          </div>
        )}
      </div>

      {/* Distance filter / sort — only meaningful once we know where the citizen is. */}
      {coords && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <span className="text-surface-500 dark:text-surface-400">Distance</span>
            <select
              value={radiusKm ?? ''}
              onChange={(e) =>
                setRadiusKm(e.target.value === '' ? undefined : Number(e.target.value))
              }
              className="rounded-lg border border-surface-300 bg-white px-2.5 py-1.5 text-sm dark:border-surface-700 dark:bg-surface-900"
            >
              {RADIUS_OPTIONS.map((opt) => (
                <option key={opt.label} value={opt.value ?? ''}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <div className="inline-flex overflow-hidden rounded-lg border border-surface-300 text-sm dark:border-surface-700">
            <button
              type="button"
              onClick={() => setSort('distance')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 ${
                sort === 'distance'
                  ? 'bg-brand-600 text-white'
                  : 'hover:bg-surface-100 dark:hover:bg-surface-700'
              }`}
            >
              <Navigation className="h-3.5 w-3.5" /> Nearest
            </button>
            <button
              type="button"
              onClick={() => setSort('rating')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 ${
                sort === 'rating'
                  ? 'bg-brand-600 text-white'
                  : 'hover:bg-surface-100 dark:hover:bg-surface-700'
              }`}
            >
              Top rated
            </button>
          </div>
        </div>
      )}

      <div className="mt-5">
        {isLoading && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
          </div>
        )}
        {isError && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900 dark:bg-red-900/30 dark:text-red-300">
            <p className="font-semibold">Could not load nearby lawyers.</p>
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
            {coords
              ? 'No lawyers with a valid office location were found for this area. Try widening the distance filter.'
              : 'No lawyers have published an office location yet. Lawyers appear here once they add their coordinates to their profile.'}
          </div>
        )}

        {!isLoading && !isError && lawyers.length > 0 && (
          <>
            {/* Distance-sorted list: name, specialization, office location, distance */}
            <ul className="space-y-3">
              {lawyers.map((l) => (
                <li
                  key={l.user_id}
                  className="rounded-2xl border border-surface-200 bg-white p-4 dark:border-surface-800 dark:bg-surface-800"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <Link
                        to={`/lawyers/${l.user_id}`}
                        className="font-semibold text-brand-700 hover:underline dark:text-brand-400"
                      >
                        {l.name}
                      </Link>
                      <p className="text-sm text-surface-600 dark:text-surface-300">
                        {specializationsOf(l) || 'General practice'}
                      </p>
                      <p className="mt-1 inline-flex items-center gap-1 text-sm text-surface-500 dark:text-surface-400">
                        <MapPin className="h-3.5 w-3.5" /> {l.city || 'Office location on file'}
                      </p>
                    </div>
                    <div className="text-right">
                      {typeof l.distance_km === 'number' && (
                        <p className="font-semibold text-brand-600 dark:text-brand-400">
                          {formatDistance(l.distance_km)}
                        </p>
                      )}
                      <p className="text-sm text-surface-500 dark:text-surface-400">
                        {formatRate(l.hourly_rate)}
                      </p>
                      <p className="text-sm text-amber-500">
                        {l.avg_rating > 0 ? `★ ${l.avg_rating.toFixed(1)}` : 'No ratings yet'}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-4">
              <MapView lawyers={lawyers} center={center} focusOnUser={Boolean(coords)} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
