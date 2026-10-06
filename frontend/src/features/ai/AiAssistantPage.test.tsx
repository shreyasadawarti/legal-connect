import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

import AiAssistantPage from '@/features/ai/AiAssistantPage'
import { aiChat } from '@/services/aiService'

vi.mock('@/services/aiService', () => ({
  aiChat: vi.fn(),
  aiPredictCategory: vi.fn(),
  aiRecommendLawyers: vi.fn(),
  aiSummarize: vi.fn(),
  aiTranslate: vi.fn(),
}))

const UNSUPPORTED = "Voice input isn't supported by your browser."
const AUTO_SEND_DELAY_MS = 1200

type SpeechErrorEvent = { error?: string }
type SpeechResult = { 0?: { transcript?: string }; isFinal?: boolean }
type SpeechInstance = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: Mock
  stop: Mock
  abort: Mock
  onresult: ((event: { results?: SpeechResult[] }) => void) | null
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

const inputBox = () => screen.getByPlaceholderText(/ask a legal question/i) as HTMLInputElement
const sendButton = () => screen.getByRole('button', { name: /^send$/i })

/**
 * Deliver a result event the way the browser does. Callers describe chunks flat for
 * readability; the API nests each transcript under index 0 of its result.
 */
function emit(
  rec: SpeechInstance,
  chunks: Array<{ transcript: string; isFinal?: boolean }>,
) {
  const results: SpeechResult[] = chunks.map((c) => ({
    0: { transcript: c.transcript },
    isFinal: c.isFinal,
  }))
  act(() => {
    rec.onresult?.({ results })
  })
}

/** Open the mic and drive one complete utterance: interim, final, then end. */
async function speak(rec: SpeechInstance, text: string) {
  fireEvent.click(micButton())
  emit(rec, [{ transcript: text, isFinal: false }])
  emit(rec, [{ transcript: text, isFinal: true }])
  act(() => {
    rec.onend?.()
  })
}

/** Advance fake timers and let react-query's microtask chain settle. */
async function tick(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms)
  })
}

describe('AiAssistantPage voice input', () => {
  beforeEach(() => {
    clearRecognition()
    vi.mocked(aiChat).mockResolvedValue({
      reply: 'An answer.',
      suggestions: [],
      category: null,
      message: null,
    } as unknown as Awaited<ReturnType<typeof aiChat>>)
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
      instances[0].onresult?.({ results: [{ 0: { transcript: 'What is a writ?' } }] })
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

describe('AiAssistantPage live transcription', () => {
  beforeEach(() => {
    clearRecognition()
    vi.useFakeTimers()
    vi.mocked(aiChat).mockResolvedValue({
      reply: 'An answer.',
      suggestions: [],
      category: null,
      message: null,
    } as unknown as Awaited<ReturnType<typeof aiChat>>)
  })

  afterEach(() => {
    vi.useRealTimers()
    clearRecognition()
    vi.clearAllMocks()
  })

  // Live typing depends on interim results; the auto-send depends on the session
  // ending at a pause. Flipping `continuous` to true would break the latter.
  it('streams provisional words but does not run a continuous session', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.click(micButton())

    expect(instances[0].interimResults).toBe(true)
    expect(instances[0].continuous).toBe(false)
  })

  it('shows a provisional word in the box while the user is still speaking', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.click(micButton())

    emit(instances[0], [{ transcript: 'What is a', isFinal: false }])

    expect(inputBox().value).toBe('What is a')
  })

  // Regression: the handler used to read results[0] only. With interim results the
  // browser appends chunks, so index 0 alone would freeze on the first word and
  // drop the rest of the sentence.
  it('keeps every chunk of a multi-chunk utterance', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.click(micButton())

    emit(instances[0], [
      { transcript: 'What is a', isFinal: true },
      { transcript: ' writ', isFinal: true },
      { transcript: ' exactly', isFinal: false },
    ])

    expect(inputBox().value).toBe('What is a writ exactly')
  })

  it('replaces provisional text with the final transcript without duplicating it', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.click(micButton())

    emit(instances[0], [{ transcript: 'Whatt is a writ', isFinal: false }])
    expect(inputBox().value).toBe('Whatt is a writ')

    emit(instances[0], [{ transcript: 'What is a writ', isFinal: true }])
    expect(inputBox().value).toBe('What is a writ')
  })

  it('keeps text typed before the mic was opened', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.change(inputBox(), { target: { value: 'Hello' } })
    fireEvent.click(micButton())

    emit(instances[0], [{ transcript: 'what is a writ', isFinal: true }])

    expect(inputBox().value).toBe('Hello what is a writ')
  })

  it('auto-sends the spoken question once the session ends', async () => {
    const instances = stubRecognition()
    renderPage()
    await speak(instances[0], 'What is a writ')

    await tick(AUTO_SEND_DELAY_MS)

    expect(aiChat).toHaveBeenCalledWith('What is a writ', [])
    expect(inputBox().value).toBe('')
  })

  it('waits briefly after the session ends instead of sending immediately', async () => {
    const instances = stubRecognition()
    renderPage()
    await speak(instances[0], 'What is a writ')

    await tick(AUTO_SEND_DELAY_MS - 1)
    expect(aiChat).not.toHaveBeenCalled()

    await tick(1)
    expect(aiChat).toHaveBeenCalledTimes(1)
  })

  it('does not send when nothing was recognised', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.click(micButton())

    act(() => {
      instances[0].onend?.()
    })
    await tick(AUTO_SEND_DELAY_MS)

    expect(aiChat).not.toHaveBeenCalled()
  })

  // The safeguard for auto-send: a pause inside one sentence splits it into two
  // utterances, so clicking the mic again must un-queue the first. Chrome reports
  // only the words spoken in the current session, so the second utterance here is
  // just the continuation and the box keeps the earlier text as its prefix.
  it('cancels a queued send and resumes speaking when the mic is clicked again', async () => {
    const instances = stubRecognition()
    renderPage()
    await speak(instances[0], 'What are my rights')

    fireEvent.click(micButton())
    expect(instances[0].start).toHaveBeenCalledTimes(2)
    expect(screen.getByText(/listening…/i)).toBeTruthy()

    emit(instances[0], [{ transcript: 'for a tenant', isFinal: false }])
    emit(instances[0], [{ transcript: 'for a tenant', isFinal: true }])
    expect(inputBox().value).toBe('What are my rights for a tenant')

    await tick(AUTO_SEND_DELAY_MS * 2)
    expect(aiChat).not.toHaveBeenCalled()

    act(() => {
      instances[0].onend?.()
    })
    await tick(AUTO_SEND_DELAY_MS)
    expect(aiChat).toHaveBeenCalledWith('What are my rights for a tenant', [])
  })

  it('cancels a queued send when the session errors', async () => {
    const instances = stubRecognition()
    renderPage()
    await speak(instances[0], 'What is a writ')

    act(() => {
      instances[0].onerror?.({ error: 'network' })
    })
    await tick(AUTO_SEND_DELAY_MS * 2)

    expect(aiChat).not.toHaveBeenCalled()
  })

  // Interim text sits in the same input as anything typed, so a manual send mid
  // sentence would ship a fragment.
  it('refuses to send while the user is still speaking', async () => {
    const instances = stubRecognition()
    renderPage()
    fireEvent.click(micButton())
    emit(instances[0], [{ transcript: 'What is', isFinal: false }])

    expect((sendButton() as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(sendButton())
    fireEvent.keyDown(inputBox(), { key: 'Enter' })

    expect(aiChat).not.toHaveBeenCalled()
  })

  it('does not fire a queued send after the page unmounts', async () => {
    const instances = stubRecognition()
    const view = renderPage()
    await speak(instances[0], 'What is a writ')

    view.unmount()
    await tick(AUTO_SEND_DELAY_MS * 2)

    expect(aiChat).not.toHaveBeenCalled()
  })
})
