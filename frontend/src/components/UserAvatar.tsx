import { useEffect, useState } from 'react'

/** Tailwind classes per size, so every avatar in the app shares one scale. */
const SIZE_CLASSES: Record<string, string> = {
  sm: 'h-9 w-9 text-xs',
  md: 'h-12 w-12 text-sm',
  lg: 'h-16 w-16 text-lg',
  xl: 'h-24 w-24 text-2xl',
}

function initialsOf(name?: string): string {
  const parts = (name ?? '').trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

interface UserAvatarProps {
  src?: string | null
  name?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

/**
 * Circular user image with an initials fallback.
 *
 * The fallback also covers a stored picture whose file has gone missing or
 * failed to load, so a broken Cloudinary URL degrades to initials instead of a
 * broken-image icon.
 */
export default function UserAvatar({ src, name, size = 'md', className = '' }: UserAvatarProps) {
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setFailed(false)
  }, [src])

  const sizeClass = SIZE_CLASSES[size] ?? SIZE_CLASSES.md
  const showImage = Boolean(src) && !failed

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-100 font-semibold text-brand-700 ring-1 ring-black/5 dark:bg-brand-900/40 dark:text-brand-300 ${sizeClass} ${className}`}
      aria-hidden="true"
    >
      {showImage ? (
        <img
          src={src as string}
          alt=""
          className="h-full w-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        initialsOf(name)
      )}
    </span>
  )
}