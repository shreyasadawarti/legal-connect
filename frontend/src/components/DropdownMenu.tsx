import { MoreVertical } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ElementType } from 'react'

export interface DropdownMenuItem {
  label: string
  onClick: () => void
  icon?: ElementType
  danger?: boolean
}

interface DropdownMenuProps {
  items: DropdownMenuItem[]
  /** Accessible label for the trigger button. */
  label?: string
  align?: 'left' | 'right'
}

/** Small kebab (three-dot) overflow menu used by the chat surfaces. */
export default function DropdownMenu({ items, label = 'More options', align = 'right' }: DropdownMenuProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(event) => {
          event.stopPropagation()
          setOpen((v) => !v)
        }}
        className="rounded-lg p-2.5 text-surface-500 transition hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-700 sm:p-1.5"
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {open && (
        <div
          role="menu"
          className={`absolute z-30 mt-1 w-48 max-w-[calc(100vw-1rem)] overflow-hidden rounded-lg border border-surface-200 bg-white py-1 shadow-lg dark:border-surface-700 dark:bg-surface-800 ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={(event) => {
                event.stopPropagation()
                setOpen(false)
                item.onClick()
              }}
              className={`flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-surface-100 dark:hover:bg-surface-700 sm:py-2 ${
                item.danger
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-surface-700 dark:text-surface-200'
              }`}
            >
              {item.icon && <item.icon className="h-4 w-4" />}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
