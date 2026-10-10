function resolveSocketUrl(): string {
  const explicit = import.meta.env.VITE_SOCKET_URL
  if (explicit) return explicit

  const apiUrl = import.meta.env.VITE_API_URL
  if (apiUrl) {
    try {
      const { protocol, host } = new URL(apiUrl, window.location.origin)
      return `${protocol === 'https:' ? 'wss:' : 'ws:'}//${host}`
    } catch {
      // fall through to the origin-based default
    }
  }

  if (import.meta.env.DEV) return 'ws://localhost:8000'
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${scheme}//${window.location.host}`
}

export const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1'
export const SOCKET_URL = resolveSocketUrl()

export const APP_NAME = 'Legal Connect'
