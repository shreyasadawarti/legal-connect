import { useMutation } from '@tanstack/react-query'
import {
  AudioLines,
  Bot,
  Loader2,
  MessageSquareText,
  Mic,
  MicOff,
  Send,
  Sparkles,
  Wand2,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import {
  aiChat,
  aiPredictCategory,
  aiRecommendLawyers,
  aiSummarize,
  aiTranslate,
} from '@/services/aiService'
import type { LawyerProfile, LegalCategory } from '@/types/platform'

type Message = { role: 'user' | 'assistant'; content: string }

const CATEGORY_NAMES: Record<LegalCategory, string> = {
  family: 'Family',
  criminal: 'Criminal',
  civil: 'Civil',
  corporate: 'Corporate',
  property: 'Property',
  tax: 'Tax',
  labor: 'Labor',
  intellectual_property: 'Intellectual Property',
  contract: 'Contract',
  personal_injury: 'Personal Injury',
  immigration: 'Immigration',
  other: 'Other',
}

// The DOM lib does not declare the Web Speech API, so the shape is described locally.
interface SpeechRecognitionAlternativeLike {
  transcript?: string
}

interface SpeechRecognitionResultLike {
  0?: SpeechRecognitionAlternativeLike
  isFinal?: boolean
}

interface SpeechRecognitionEventLike {
  results?: ArrayLike<SpeechRecognitionResultLike>
}

interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onend: (() => void) | null
  onerror: ((event: { error?: string }) => void) | null
}

// A trailing word can land just after Chrome decides the utterance ended, so the
// auto-send waits a moment rather than firing inside the `onend` handler.
const AUTO_SEND_DELAY_MS = 1200

type RecognitionConstructor = new () => SpeechRecognitionLike

function getRecognitionCtor(): RecognitionConstructor | null {
  type WindowWithSpeech = Window & {
    SpeechRecognition?: RecognitionConstructor
    webkitSpeechRecognition?: RecognitionConstructor
  }
  const w = window as WindowWithSpeech
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

const SPEECH_ERRORS: Record<string, string> = {
  'no-speech': "I didn't catch anything. Please try again.",
  'audio-capture': 'No microphone was found. Check your audio input device.',
  'not-allowed': 'Microphone access was denied. Allow it in your browser settings to use voice input.',
  'service-not-allowed':
    'Your browser blocked microphone access. Enable it in the site settings for this page.',
  network: 'Voice recognition needs an internet connection.',
}

function AssistantTab() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hello! I am your Legal Connect assistant. Ask me any legal question in plain language.',
    },
  ])
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [listening, setListening] = useState(false)
  const [pendingSpeech, setPendingSpeech] = useState<string | null>(null)
  const [speechSupported] = useState(() => getRecognitionCtor() !== null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  // Whatever was already in the box before the mic opened, so starting a session
  // does not wipe a half-typed question.
  const baseTextRef = useRef('')
  // The full composed box value after the most recent result event. `onend` runs in
  // the mount effect and cannot read fresh state, so it reads this instead.
  const spokenRef = useRef('')

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const Ctor = getRecognitionCtor()
    if (!Ctor) return
    const rec = new Ctor()
    recognitionRef.current = rec
    // `interimResults` streams words into the box while the user is still speaking.
    // `continuous` stays false so a pause ends the session, which is what triggers
    // the auto-send.
    rec.continuous = false
    rec.interimResults = true
    rec.lang = navigator.language
    rec.onresult = (event) => {
      const results = event?.results
      if (!results || results.length === 0) return
      let committed = ''
      let provisional = ''
      // The whole list is walked on every event. Reading only index 0, as this used
      // to, silently discarded every chunk after the first within one session.
      for (let i = 0; i < results.length; i += 1) {
        const result = results[i]
        const text = result?.[0]?.transcript || ''
        // Only an explicit `isFinal === false` is provisional. Browsers always set
        // the flag, so treating a missing one as final keeps a settled transcript
        // from being discarded.
        if (result?.isFinal === false) {
          provisional += text
        } else {
          committed += text
        }
      }
      const base = baseTextRef.current.trim()
      const spoken = [base, committed + provisional].filter(Boolean).join(' ')
      spokenRef.current = spoken
      setInput(spoken)
    }
    rec.onend = () => {
      setListening(false)
      const spoken = spokenRef.current.trim()
      spokenRef.current = ''
      if (!spoken) return
      setPendingSpeech(spoken)
    }
    rec.onerror = (e) => {
      setListening(false)
      // A failed session must not leave a queued message to fire on its own.
      setPendingSpeech(null)
      // `aborted` is raised by our own stop()/unmount cleanup, so it stays silent.
      if (!e.error || e.error === 'aborted') return
      setError(
        SPEECH_ERRORS[e.error] ||
          'Voice input failed. Please try again or type your question.',
      )
    }
    return () => {
      recognitionRef.current?.abort()
      recognitionRef.current = null
    }
  }, [])

  const chat = useMutation({
    mutationFn: async (text: string) => {
      const history = messages.slice(1).map((m) => ({ role: m.role, content: m.content }))
      return aiChat(text, history)
    },
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
      setError('')
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(
        err.response?.data?.detail || 'AI is temporarily unavailable. Please try again later.',
      )
    },
  })

  const submit = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || chat.isPending) return
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }])
    setInput('')
    setError('')
    chat.mutate(trimmed)
  }

  // The auto-send timer fires outside the mount effect, which closed over the first
  // render's `messages`. This ref always points at the current `submit`.
  const submitRef = useRef(submit)
  useEffect(() => {
    submitRef.current = submit
  })

  // Queued auto-send. Keyed on `pendingSpeech`, so clearing it cancels the timer
  // through the effect cleanup.
  useEffect(() => {
    if (!pendingSpeech) return
    const timer = setTimeout(() => {
      setPendingSpeech(null)
      submitRef.current(pendingSpeech)
    }, AUTO_SEND_DELAY_MS)
    return () => clearTimeout(timer)
  }, [pendingSpeech])

  const startListening = () => {
    const rec = recognitionRef.current
    if (!rec) {
      setError('Voice input is not supported by this browser. Try Chrome or Edge.')
      return
    }
    // Cancels any queued auto-send and resumes appending to what is already there.
    setPendingSpeech(null)
    baseTextRef.current = input
    spokenRef.current = ''
    setError('')
    try {
      rec.start()
      setListening(true)
    } catch {
      // start() throws InvalidStateError if a session is already active.
      setListening(false)
    }
  }

  const toggleMic = () => {
    // A queued message is not final: click the mic again to keep speaking instead.
    if (pendingSpeech) {
      startListening()
      return
    }
    if (listening) {
      recognitionRef.current?.stop?.()
      setListening(false)
      return
    }
    startListening()
  }

  const send = () => {
    // Never ship a half-spoken sentence, and never race a queued auto-send.
    if (listening || pendingSpeech) return
    submit(input)
  }

  return (
    <div className="flex h-[60vh] min-h-[20rem] flex-col sm:h-[28rem]">
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === 'user'
                  ? 'bg-brand-600 text-white'
                  : 'border border-surface-200 bg-surface-50 dark:border-surface-700 dark:bg-surface-900'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {chat.isPending && (
          <div className="flex items-center gap-2 text-sm text-surface-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
          </div>
        )}
        {error && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-600 dark:border-red-900 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-2 border-t border-surface-200 pt-3 dark:border-surface-700">
        <button
          type="button"
          onClick={toggleMic}
          title={listening ? 'Stop listening' : 'Speak'}
          aria-label={listening ? 'Stop listening' : 'Start voice input'}
          aria-pressed={listening}
          disabled={!speechSupported}
          className={`rounded-full p-2.5 transition ${
            listening
              ? 'bg-red-100 text-red-600 dark:bg-red-900/30'
              : 'bg-surface-100 text-surface-600 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-300'
          } disabled:opacity-50`}
        >
          {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask a legal question…"
          className="min-w-0 flex-1 rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
        />
        <button
          type="button"
          onClick={send}
          aria-label="Send"
          disabled={!input.trim() || chat.isPending || listening || !!pendingSpeech}
          className="rounded-lg bg-brand-600 px-3 py-2 text-white hover:bg-brand-700 disabled:opacity-60"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      {(listening || pendingSpeech) && (
        <p
          aria-live="polite"
          className="mt-1 flex items-center gap-1 text-xs text-surface-500"
        >
          <AudioLines className="h-3 w-3 animate-pulse" />
          {listening
            ? 'Listening… speak now'
            : 'Sending… click the mic to keep speaking instead'}
        </p>
      )}
      {!speechSupported && (
        <p className="mt-1 flex items-center gap-1 text-xs text-surface-400">
          <AudioLines className="h-3 w-3" /> Voice input isn't supported by your browser.
        </p>
      )}
    </div>
  )
}

function SummarizerCard() {
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [error, setError] = useState('')
  const run = useMutation({
    mutationFn: () => aiSummarize(text),
    onSuccess: (d) => {
      setSummary(d.summary)
      setError('')
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Could not summarize. AI is not configured.')
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <h3 className="flex items-center gap-2 font-semibold">
        <Wand2 className="h-5 w-5 text-brand-600" /> Summarize a document
      </h3>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        placeholder="Paste a legal document or clause…"
        className="mt-3 w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
      />
      <button
        type="button"
        onClick={() => run.mutate()}
        disabled={!text.trim() || run.isPending}
        className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
      >
        {run.isPending ? 'Summarizing…' : 'Summarize'}
      </button>
      {summary && (
        <div className="mt-3 rounded-lg bg-surface-50 p-3 text-sm dark:bg-surface-900">
          {summary}
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  )
}

function PredictorCard() {
  const [description, setDescription] = useState('')
  const [result, setResult] = useState<{ category: LegalCategory; confidence: number; explanation: string } | null>(
    null,
  )
  const [error, setError] = useState('')
  const run = useMutation({
    mutationFn: () => aiPredictCategory(description),
    onSuccess: (d) => {
      setResult(d)
      setError('')
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Could not predict. AI is not configured.')
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <h3 className="flex items-center gap-2 font-semibold">
        <Sparkles className="h-5 w-5 text-brand-600" /> Predict legal category
      </h3>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
        placeholder="Describe your legal issue briefly…"
        className="mt-3 w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
      />
      <button
        type="button"
        onClick={() => run.mutate()}
        disabled={!description.trim() || run.isPending}
        className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
      >
        {run.isPending ? 'Predicting…' : 'Predict'}
      </button>
      {result && (
        <div className="mt-3 rounded-lg bg-surface-50 p-3 text-sm dark:bg-surface-900">
          <p>
            <span className="font-semibold">{CATEGORY_NAMES[result.category]}</span>{' '}
            <span className="text-surface-500">({Math.round(result.confidence * 100)}% confidence)</span>
          </p>
          {result.explanation && <p className="mt-1 text-surface-500">{result.explanation}</p>}
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  )
}

function TranslatorCard() {
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('Hindi')
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const run = useMutation({
    mutationFn: () => aiTranslate(text, language),
    onSuccess: (d) => {
      setResult(d.translated)
      setError('')
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Could not translate. AI is not configured.')
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <h3 className="flex items-center gap-2 font-semibold">
        <MessageSquareText className="h-5 w-5 text-brand-600" /> Translate legal text
      </h3>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder="Text to translate…"
        className="mt-3 w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
      />
      <div className="mt-2 flex items-center gap-2">
        <span className="text-sm text-surface-500">Into</span>
        <input
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded-lg border border-surface-300 bg-surface-50 px-3 py-1.5 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
        />
      </div>
      <button
        type="button"
        onClick={() => run.mutate()}
        disabled={!text.trim() || run.isPending}
        className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
      >
        {run.isPending ? 'Translating…' : 'Translate'}
      </button>
      {result && (
        <div className="mt-3 rounded-lg bg-surface-50 p-3 text-sm dark:bg-surface-900">{result}</div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  )
}

function RecommenderCard() {
  const [description, setDescription] = useState('')
  const [result, setResult] = useState<LawyerProfile[]>([])
  const [error, setError] = useState('')
  const run = useMutation({
    mutationFn: () => aiRecommendLawyers(description, 5),
    onSuccess: (d) => {
      setResult(d.recommendations)
      setError('')
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Could not recommend. AI is not configured.')
    },
  })

  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <h3 className="flex items-center gap-2 font-semibold">
        <Bot className="h-5 w-5 text-brand-600" /> Get lawyer recommendations
      </h3>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={2}
        placeholder="Tell us about your case…"
        className="mt-3 w-full rounded-lg border border-surface-300 bg-surface-50 px-3 py-2 text-sm outline-none focus:border-brand-500 dark:border-surface-700 dark:bg-surface-900"
      />
      <button
        type="button"
        onClick={() => run.mutate()}
        disabled={!description.trim() || run.isPending}
        className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
      >
        {run.isPending ? 'Finding…' : 'Recommend lawyers'}
      </button>
      {result.length > 0 && (
        <ul className="mt-3 space-y-2">
          {result.map((l) => (
            <li
              key={l.user_id}
              className="rounded-lg border border-surface-200 p-3 text-sm dark:border-surface-700"
            >
              <p className="font-medium">{l.name}</p>
              <p className="text-xs text-surface-500">
                {l.city || '—'} · ₹{l.hourly_rate}/hr · {CATEGORY_NAMES[l.categories[0]]}
              </p>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  )
}

type TabId = 'assistant' | 'tools'

export default function AiAssistantPage() {
  const [tab, setTab] = useState<TabId>('assistant')

  return (
    <div>
      <h1 className="text-2xl font-bold">AI Assistant</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        AI-powered legal guidance, powered by an OpenAI-compatible provider.
      </p>

      <div className="mt-5 flex gap-2">
        <button
          type="button"
          onClick={() => setTab('assistant')}
          className={`rounded-lg px-4 py-2 text-sm font-semibold ${
            tab === 'assistant'
              ? 'bg-brand-600 text-white'
              : 'border border-surface-300 hover:bg-surface-100 dark:border-surface-700'
          }`}
        >
          Assistant
        </button>
        <button
          type="button"
          onClick={() => setTab('tools')}
          className={`rounded-lg px-4 py-2 text-sm font-semibold ${
            tab === 'tools'
              ? 'bg-brand-600 text-white'
              : 'border border-surface-300 hover:bg-surface-100 dark:border-surface-700'
          }`}
        >
          Tools
        </button>
      </div>

      <div className="mt-5">
        {tab === 'assistant' ? (
          <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
            <AssistantTab />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            <SummarizerCard />
            <PredictorCard />
            <TranslatorCard />
            <RecommenderCard />
          </div>
        )}
      </div>
    </div>
  )
}
