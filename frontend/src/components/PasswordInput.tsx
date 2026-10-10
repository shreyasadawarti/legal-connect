import { Eye, EyeOff, Lock } from 'lucide-react'
import { forwardRef, useState } from 'react'
import type { InputHTMLAttributes } from 'react'

const BASE_INPUT_CLASS =
  'w-full rounded-lg border border-surface-300 bg-surface-50 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-surface-700 dark:bg-surface-900'

interface PasswordInputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Render the leading lock icon and pad the text accordingly. */
  withLockIcon?: boolean
  /** Classes applied to the relative wrapper that positions the icons. */
  containerClassName?: string
}

/**
 * Password field with an eye / eye-off visibility toggle.
 *
 * Renders its own `relative` wrapper (the leading lock and trailing toggle are
 * absolutely positioned inside it) so callers must not wrap it in another
 * `relative` div. Works with `react-hook-form`'s `register(...)` / `field(...)`
 * spreads because the ref is forwarded to the underlying input.
 */
const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ withLockIcon = true, containerClassName = '', className = '', ...props }, ref) => {
    const [visible, setVisible] = useState(false)

    return (
      <div className={`relative ${containerClassName}`}>
        {withLockIcon && (
          <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
        )}
        <input
          ref={ref}
          {...props}
          type={visible ? 'text' : 'password'}
          className={`${BASE_INPUT_CLASS} pr-10 ${withLockIcon ? 'pl-10' : 'pl-3'} ${className}`}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-surface-400 transition hover:text-surface-600 dark:hover:text-surface-200"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    )
  },
)

PasswordInput.displayName = 'PasswordInput'

export default PasswordInput
