import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

import AiAssistantPage from '@/features/ai/AiAssistantPage'

vi.mock('@/services/aiService', () => ({
  aiChat: vi.fn(),
  aiPredictCategory: vi.fn(),
  aiRecommendLawyers: vi.fn(),
  aiSummarize: vi.fn(),
  aiTranslate: vi.fn(),
}))

const UNSUPPORTED = "Voice input isn't supported by your browser."

type SpeechErrorEvent = { error?: string }
type SpeechInstance = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: Mock
  stop: Mock
  abort: Mock
  onresult: ((event: { results?: Array<Array<{ transcript?: string }>> }) => void) | null
  onend: (() => void) | null
  onerror: ((event: SpeechErrorEvent) => void) | null
}

/** Minimal stand-in for the Web Speech API, recording every constructed instance. */
function stubRecognition() {
  const instances: SpeechInstance[] = []
  class FakeRecognition {
    continuous = false
    interimResults = false
    lang = ''
    onresult: SpeechInstance['onresult'] = null
    onend: SpeechInstance['onend'] = null
    onerror: SpeechInstance['onerror'] = null
    start = vi.fn()
    stop = vi.fn()
    abort = vi.fn()

    constructor() {
      instances.push(this)
    }
  }
  ;(window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition
  return instances
}

function clearRecognition() {
  const w = window as unknown as Record<string, unknown>
  delete w.SpeechRecognition
  delete w.webkitSpeechRecognition
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AiAssistantPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// The button's accessible name reflects the action it performs, so it changes to
// "Stop listening" while a session is running.
const micButton = () =>
  screen.getByRole('button', { name: /voice input|stop listening/i })

describe('AiAssistantPage voice input', () => {
  beforeEach(() => {
    clearRecognition()
  })

  afterEach(() => {
    clearRecognition()
    vi.clearAllMocks()
  })

  // Regression: the warning used to be driven by `recognitionRef.current`, a ref read
  // during the first render. The instance is created in a mount effect, so the first
  // render always saw `null` and painted "unsupported" even in Chrome, and because
  // mutating a ref does not re-render, the warning never went away.
  it('does not claim the browser is unsupported when the Web Speech API exists', () => {
    stubRecognition()
    renderPage()
    expect(screen.queryByText(UNSUPPORTED)).toBeNull()
  })

  it('detects the prefixed webkitSpeechRecognition constructor', () => {
    const instances = stubRecognition()
    renderPage()
    expect(instances).toHaveLength(1)
  })

  it('prefers the unprefixed SpeechRecognition constructor when present', () => {
    const instances = stubRecognition()
    ;(window as unknown as Record<string, unknown>).SpeechRecognition = class {
      continuous = false
      interimResults = false
      lang = ''
      onresult = null
      onend = null
      onerror = null
      start = vi.fn()
      stop = vi.fn()
      abort = vi.fn()

      constructor() {
        instances.push(this as unknown as SpeechInstance)
      }
    }
    renderPage()
    expect(screen.queryByText(UNSUPPORTED)).toBeNull()
    expect(instances).toHaveLength(1)
  })

  it('still reports an unsupported browser when no constructor exists', () => {
    renderPage()
    expect(screen.getByText(UNSUPPORTED)).toBeTruthy()
  })

  it('starts listening on mic click and stops on a second click', async () => {
    const instances = stubRecognition()
    renderPage()
    await userEvent.click(micButton())
    expect(instances[0].start).toHaveBeenCalledTimes(1)

    await userEvent.click(micButton())
    expect(instances[0].stop).toHaveBeenCalledTimes(1)
  })

  it('puts the recognised transcript into the chat input', () => {
    const instances = stubRecognition()
    renderPage()

    act(() => {
      instances[0].onresult?.({ results: [[{ transcript: 'What is a writ?' }]] })
    })

    expect((screen.getByPlaceholderText(/ask a legal question/i) as HTMLInputElement).value)
      .toBe('What is a writ?')
  })

  it('surfaces a microphone-permission failure instead of silently stopping', () => {
    const instances = stubRecognition()
    renderPage()

    act(() => {
      instances[0].onerror?.({ error: 'not-allowed' })
    })

    expect(screen.getByText(/microphone access was denied/i)).toBeTruthy()
  })

  it('stays silent for an aborted session, which our own cleanup triggers', () => {
    const instances = stubRecognition()
    renderPage()

    act(() => {
      instances[0].onerror?.({ error: 'aborted' })
    })

    expect(screen.queryByText(/microphone access was denied/i)).toBeNull()
  })

  it('does not throw when start() is called on an already-active session', async () => {
    const instances = stubRecognition()
    renderPage()
    const rec = instances[0]
    rec.start.mockImplementation(() => {
      throw new DOMException('already started', 'InvalidStateError')
    })

    expect(() => fireEvent.click(micButton())).not.toThrow()
    expect(micButton().getAttribute('aria-pressed')).toBe('false')
  })

  it('disables the mic button when the browser has no Web Speech API', () => {
    renderPage()
    expect((micButton() as HTMLButtonElement).disabled).toBe(true)
  })
})
