import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

const URL_RE = /https?:\/\/[^\s<>"']+/g

function sameOriginAsCurrent(href: string): boolean {
  try {
    return new URL(href, window.location.origin).origin === window.location.origin
  } catch {
    return false
  }
}

export default function MessageContent({ text }: { text: string }) {
  const navigate = useNavigate()
  const parts: ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null
  URL_RE.lastIndex = 0
  while ((match = URL_RE.exec(text)) !== null) {
    const url = match[0]
    if (match.index > last) parts.push(text.slice(last, match.index))
    if (sameOriginAsCurrent(url)) {
      parts.push(
        <a
          key={match.index}
          href={url}
          className="break-all underline"
          onClick={(e) => {
            e.preventDefault()
            const parsed = new URL(url, window.location.origin)
            navigate(parsed.pathname + parsed.search + parsed.hash)
          }}
        >
          {url}
        </a>,
      )
    } else {
      parts.push(
        <a
          key={match.index}
          href={url}
          target="_blank"
          rel="noreferrer noopener"
          className="break-all underline"
        >
          {url}
        </a>,
      )
    }
    last = match.index + url.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return <>{parts}</>
}