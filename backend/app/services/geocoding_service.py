"""City-name -> coordinates resolution with graceful degradation.

A lawyer profile may store an office city name but no coordinates. When a
citizen runs a nearest-first "nearby lawyers" search, profiles without
coordinates would be silently dropped even when the lawyer practises in the
citizen's own city. This service resolves such city names to real coordinates,
which the router then persists on the profile so they are verified once and
reused forever.

Coordinates come from OpenStreetMap's free Nominatim API (no API key; it only
asks for a descriptive User-Agent and modest request rates). Failures -- a
timeout, a non-200 response, an unknown city, or an unconfigured provider --
return None, so the profile simply stays out of distance-based results instead
of breaking the request.
"""

import logging
import time
from typing import Optional
from urllib.parse import quote_plus

import httpx

from app.config import settings

logger = logging.getLogger("legalconnect.geocoding")

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"

# Nominatim's usage policy asks clients to identify themselves with a UA that
# includes contact info; this app has no public contact address, so a descriptive
# name is used.
_GEOCODING_USER_AGENT = "legal-connect/1.0 (college project)"

# Failed lookups are retried at most once an hour so a flaky network does not
# hammer the public service on every request.
RETRY_AFTER_SECONDS = 3600.0

_cache: dict[str, Optional[tuple[float, float]]] = {}
_next_retry: dict[str, float] = {}


def _normalize(city: str) -> str:
    return " ".join((city or "").strip().lower().split())


class GeocodingService:
    async def geocode_city(self, city: str) -> Optional[tuple[float, float]]:
        """Resolve an Indian city name to (latitude, longitude), or None."""
        key = _normalize(city)
        if not key:
            return None
        if key in _cache:
            return _cache[key]
        now = time.monotonic()
        if _next_retry.get(key, 0.0) > now:
            return _cache.get(key)
        coords = await self._lookup_nominatim(f"{key}, india")
        _cache[key] = coords
        if coords is None:
            _next_retry[key] = now + RETRY_AFTER_SECONDS
        return coords

    async def _lookup_nominatim(
        self, query: str, *, max_results: int = 1
    ) -> Optional[tuple[float, float]]:
        params = {
            "q": query,
            "format": "json",
            "limit": max_results,
            "countrycodes": "in",
            "accept-language": "en",
        }
        headers = {"User-Agent": _GEOCODING_USER_AGENT}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    NOMINATIM_SEARCH_URL, params=params, headers=headers
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Geocoding lookup for %r failed (%s): %s",
                query,
                type(exc).__name__,
                exc,
            )
            return None
        if resp.status_code != 200:
            logger.warning(
                "Geocoding lookup for %r returned HTTP %s", query, resp.status_code
            )
            return None
        try:
            rows = resp.json()
        except Exception:  # noqa: BLE001
            logger.warning("Geocoding lookup for %r returned unparsable JSON", query)
            return None
        if not rows:
            return None
        try:
            lat = float(rows[0]["lat"])
            lon = float(rows[0]["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None
        return (lat, lon)


geocoding_service = GeocodingService()


async def ensure_missing_coordinates(db) -> int:
    """Resolve and persist coordinates for profiles that have a city but none.

    Best-effort: unknown cities and network failures leave the profile untouched
    (and therefore excluded from distance-based results). Returns the number of
    profiles that gained coordinates. Callers commit via their DB session.
    """
    from app.repositories.lawyer_repository import LawyerRepository

    repo = LawyerRepository(db)
    missing = await repo.list_with_city_but_no_coords()
    resolved = 0
    for profile in missing:
        coords = await geocoding_service.geocode_city(profile["city"])
        if coords is None:
            continue
        await repo.update(
            profile["user_id"], {"latitude": coords[0], "longitude": coords[1]}
        )
        resolved += 1
    return resolved