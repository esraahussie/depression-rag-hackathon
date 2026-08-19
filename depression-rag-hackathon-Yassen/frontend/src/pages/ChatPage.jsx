import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useChat } from '../chatContext'
import { useLanguage } from '../i18n'
import { resolveSourceUrl } from '../sourceUrls'

function formatRelevance(score) {
  if (score == null) return null
  return `${Math.round(score * 100)}%`
}

function stripForSpeech(text) {
  return String(text || '')
    .replace(/\[\d+\]/g, ' ')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/[`#]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function renderAnswerWithCitations(text, onCitationClick) {
  if (!text) return null
  const parts = text.split(/(\[\d+\]|\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    const cite = part.match(/^\[(\d+)\]$/)
    if (cite) {
      const id = cite[1]
      return (
        <button
          key={`cite-${i}-${id}`}
          type="button"
          className="citation-marker"
          onClick={() => onCitationClick(id)}
          aria-label={`Go to source ${id}`}
        >
          [{id}]
        </button>
      )
    }
    const bold = part.match(/^\*\*([^*]+)\*\*$/)
    if (bold) {
      return <strong key={`b-${i}`}>{bold[1]}</strong>
    }
    return <React.Fragment key={`t-${i}`}>{part}</React.Fragment>
  })
}

function SourceCard({ source, highlighted, t }) {
  const page = source.page != null ? source.page : 'N/A'
  const chunk = source.chunk != null ? source.chunk : 'N/A'
  const relevance = formatRelevance(source.relevance_score)
  const url = source.source_url || resolveSourceUrl(source.pdf, source.page)

  return (
    <li
      id={`source-${source.citation_id}`}
      className={`source-item ${highlighted ? 'source-highlight' : ''}`}
    >
      <div className="source-header">
        <span className="source-citation-id">[{source.citation_id}]</span>
        {url ? (
          <a
            className="source-name source-name-link"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {source.name}
          </a>
        ) : (
          <span className="source-name">{source.name}</span>
        )}
      </div>
      <p className="source-filename">{source.pdf}</p>
      {url && (
        <a
          className="source-url"
          href={url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {t.openSource || 'Open guideline'}
        </a>
      )}
      <div className="source-meta">
        <span className="source-meta-badge">{t.page} {page}</span>
        <span className="source-meta-badge">{t.chunk} {chunk}</span>
        {relevance != null && (
          <span className="source-meta-badge source-meta-relevance">{t.relevance} {relevance}</span>
        )}
      </div>
    </li>
  )
}

function pickVoice(voices, isAr) {
  if (!voices?.length) return null
  if (isAr) {
    const arabic = voices.filter((v) => v.lang?.toLowerCase().startsWith('ar'))
    const egyptianName = /egypt|egyptian|hoda|cairo|masr|مصري/i
    return (
      arabic.find((v) => v.lang?.toLowerCase() === 'ar-eg') ||
      arabic.find((v) => egyptianName.test(`${v.name} ${v.lang}`)) ||
      arabic[0] ||
      null
    )
  }
  return voices.find((v) => v.lang?.toLowerCase().startsWith('en')) || null
}

function useVoices() {
  const [voices, setVoices] = React.useState(() => (
    typeof window !== 'undefined' && window.speechSynthesis
      ? window.speechSynthesis.getVoices()
      : []
  ))

  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return undefined
    const load = () => setVoices(window.speechSynthesis.getVoices())
    load()
    window.speechSynthesis.addEventListener('voiceschanged', load)
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load)
  }, [])

  return voices
}

function useSpeechSynthesis(isAr) {
  const [speakingId, setSpeakingId] = React.useState(null)
  const voices = useVoices()
  const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

  const speak = React.useCallback((text, messageId) => {
    if (!isSupported) return
    window.speechSynthesis.cancel()

    const cleaned = stripForSpeech(text)
    if (!cleaned) return

    const arabicInText = /[\u0600-\u06FF]/.test(cleaned)
    const speakAr = isAr || arabicInText
    const utterance = new SpeechSynthesisUtterance(cleaned)
    utterance.rate = speakAr ? 0.95 : 1
    utterance.pitch = 1
    utterance.lang = speakAr ? 'ar-EG' : 'en-US'
    const voice = pickVoice(voices, speakAr)
    if (voice) utterance.voice = voice
    utterance.onstart = () => setSpeakingId(messageId)
    utterance.onend = () => setSpeakingId(null)
    utterance.onerror = () => setSpeakingId(null)

    window.speechSynthesis.speak(utterance)
  }, [isSupported, isAr, voices])

  const stop = React.useCallback(() => {
    if (!isSupported) return
    window.speechSynthesis.cancel()
    setSpeakingId(null)
  }, [isSupported])

  React.useEffect(() => {
    return () => {
      if (isSupported) window.speechSynthesis.cancel()
    }
  }, [isSupported])

  return { speak, stop, speakingId, isSupported }
}

function SpeakerButton({ text, messageId, speech, t }) {
  if (!speech.isSupported) return null
  const isSpeaking = speech.speakingId === messageId

  const handleClick = () => {
    if (isSpeaking) {
      speech.stop()
    } else {
      speech.speak(text, messageId)
    }
  }

  return (
    <button
      type="button"
      className={`speaker-btn ${isSpeaking ? 'speaker-btn-active' : ''}`}
      onClick={handleClick}
      aria-label={isSpeaking ? t.stopReading : t.readAloud}
      title={isSpeaking ? t.stopReading : t.readAloud}
    >
      {isSpeaking ? (
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 9v6h4l5 4V5L8 9H4z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M17 8.5a5 5 0 010 7"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      )}
    </button>
  )
}

function AssistantMessage({ message, messageId, speech, autoSpeak, pendingSpeakId, setPendingSpeakId, t }) {
  const [highlightedId, setHighlightedId] = React.useState(null)
  const hasAutoSpoken = React.useRef(false)

  const handleCitationClick = (id) => {
    setHighlightedId(id)
    const sourceEl = document.getElementById(`source-${id}`)
    const detailsEl = sourceEl?.closest('details')
    if (detailsEl && !detailsEl.open) detailsEl.open = true
    sourceEl?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    setTimeout(() => setHighlightedId(null), 2000)
  }

  React.useEffect(() => {
    const shouldSpeak = (
      autoSpeak
      && !message.loading
      && message.content
      && pendingSpeakId
      && (pendingSpeakId === message.id || pendingSpeakId === messageId)
      && !hasAutoSpoken.current
    )
    if (shouldSpeak) {
      hasAutoSpoken.current = true
      setPendingSpeakId(null)
      speech.speak(message.content, messageId)
    }
  }, [autoSpeak, message.loading, message.content, message.id, messageId, pendingSpeakId, setPendingSpeakId, speech])

  const confidencePct =
    message.confidence != null ? `${Math.round(message.confidence * 100)}%` : null

  return (
    <div className="message-row assistant">
      <div className="avatar assistant-avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path
            d="M12 4c-2.8 0-4.8 2-4.8 4.8 0 3.2 2.4 4.4 4.8 7.2 2.4-2.8 4.8-4 4.8-7.2C16.8 6 14.8 4 12 4z"
            fill="currentColor"
          />
        </svg>
      </div>
      <div className={`message-bubble assistant-bubble ${message.loading ? 'assistant-bubble-loading' : ''}`}>
        {message.loading ? (
          <div className="typing-indicator" aria-label="Loading response">
            <span /><span /><span />
          </div>
        ) : (
          <>
            <div className="message-text-row">
              <p className="message-text">
                {renderAnswerWithCitations(message.content, handleCitationClick)}
              </p>
              <SpeakerButton text={message.content} messageId={messageId} speech={speech} t={t} />
            </div>
            {confidencePct != null && message.status !== 'out_of_scope' && (
              <p className="confidence-badge" aria-label={`${t.confidence} ${confidencePct}`}>
                {t.confidence}: <strong>{confidencePct}</strong>
              </p>
            )}
            {message.sources?.length > 0 && (
              <details className="sources-block">
                <summary className="sources-title">
                  {t.supportingSources}
                  <span className="sources-count">{message.sources.length}</span>
                </summary>
                <ul className="sources-list">
                  {message.sources.map((source) => (
                    <SourceCard
                      key={source.citation_id}
                      source={source}
                      highlighted={String(highlightedId) === String(source.citation_id)}
                      t={t}
                    />
                  ))}
                </ul>
              </details>
            )}
            {message.additionalSources?.length > 0 && (
              <details className="sources-block sources-additional">
                <summary className="sources-title">
                  {t.additionalSources}
                  <span className="sources-count">{message.additionalSources.length}</span>
                </summary>
                <ul className="sources-list">
                  {message.additionalSources.map((source) => (
                    <SourceCard key={`add-${source.citation_id}`} source={source} highlighted={false} t={t} />
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function MessageBubble({ message, messageId, speech, autoSpeak, pendingSpeakId, setPendingSpeakId, t }) {
  if (message.role === 'user') {
    return (
      <div className="message-row user">
        <div className="message-bubble user-bubble">
          <p className="message-text">{message.content}</p>
        </div>
      </div>
    )
  }
  return (
    <AssistantMessage
      message={message}
      messageId={messageId}
      speech={speech}
      autoSpeak={autoSpeak}
      pendingSpeakId={pendingSpeakId}
      setPendingSpeakId={setPendingSpeakId}
      t={t}
    />
  )
}

function useSpeechRecognition(onResult, isAr) {
  const recognitionRef = React.useRef(null)
  const [isListening, setIsListening] = React.useState(false)
  const [isSupported, setIsSupported] = React.useState(true)

  React.useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setIsSupported(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = isAr ? 'ar-EG' : 'en-US'

    recognition.onresult = (event) => {
      let transcript = ''
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript
      }
      onResult(transcript)
    }

    recognition.onend = () => setIsListening(false)
    recognition.onerror = () => setIsListening(false)

    recognitionRef.current = recognition
    return () => {
      recognition.stop()
    }
  }, [onResult, isAr])

  const startListening = () => {
    if (!recognitionRef.current || isListening) return
    setIsListening(true)
    recognitionRef.current.start()
  }

  const stopListening = () => {
    if (!recognitionRef.current) return
    recognitionRef.current.stop()
  }

  return { isListening, isSupported, startListening, stopListening }
}

export default function ChatPage() {
  const { t, isAr } = useLanguage()
  const {
    messages,
    autoSpeak,
    setAutoSpeak,
    pendingSpeakId,
    setPendingSpeakId,
    isLoading,
    sendMessage,
    appendLocalExchange,
  } = useChat()
  const [input, setInput] = React.useState('')
  const chatEndRef = React.useRef(null)
  const inputRef = React.useRef(null)
  const speech = useSpeechSynthesis(isAr)
  const location = useLocation()
  const navigate = useNavigate()

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const autoQuerySentRef = React.useRef(false)

  React.useEffect(() => {
    const { autoQuery, autoExplanation, autoExplanationQuestion } = location.state || {}
    if ((autoQuery || autoExplanation) && !autoQuerySentRef.current) {
      autoQuerySentRef.current = true
      navigate('/chat', { replace: true, state: {} })

      if (autoExplanation) {
        appendLocalExchange(autoExplanationQuestion || t.askGuideline, autoExplanation)
      }

      if (autoQuery) {
        sendMessage(autoQuery)
      }
    }
  }, [appendLocalExchange, location.state, navigate, sendMessage, t.askGuideline])

  const handleSpeechResult = React.useCallback((transcript) => {
    setInput(transcript)
  }, [])

  const { isListening, isSupported, startListening, stopListening } =
    useSpeechRecognition(handleSpeechResult, isAr)

  const handleMicClick = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    sendMessage(input)
    setInput('')
  }

  React.useEffect(() => {
    if (!isLoading) inputRef.current?.focus()
  }, [isLoading])

  const isEmpty = messages.length === 0

  return (
    <div className="chat-page">
      <header className="page-header">
        <div>
          <h2 className="page-title">{t.pageTitle}</h2>
          <p className="page-subtitle">{t.pageSubtitle}</p>
        </div>
        {speech.isSupported && (
          <label className="auto-speak-toggle">
            <input
              type="checkbox"
              checked={autoSpeak}
              onChange={(e) => {
                setAutoSpeak(e.target.checked)
                if (!e.target.checked) speech.stop()
              }}
            />
            {t.autoRead}
          </label>
        )}
      </header>

      <div className="chat-container">
        <div className="chat-messages" role="log" aria-live="polite" aria-label="Chat messages">
          {isEmpty ? (
            <div className="chat-empty">
              <div className="empty-icon" aria-hidden="true">
                <svg viewBox="0 0 48 48" fill="none">
                  <circle cx="24" cy="24" r="22" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
                  <path
                    d="M16 22c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  <path d="M24 30v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </div>
              <h3>{t.emptyTitle}</h3>
              <p>{t.emptyBody}</p>
              <div className="example-questions">
                {t.examples.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="example-btn"
                    onClick={() => sendMessage(q)}
                    disabled={isLoading}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <MessageBubble
                key={msg.id || i}
                message={msg}
                messageId={msg.id || i}
                speech={speech}
                autoSpeak={autoSpeak}
                pendingSpeakId={pendingSpeakId}
                setPendingSpeakId={setPendingSpeakId}
                t={t}
              />
            ))
          )}
          <div ref={chatEndRef} />
        </div>

        <form className="chat-input-bar" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder={isListening ? t.listening : t.placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            aria-label={t.placeholder}
            dir="auto"
          />
          {isSupported && (
            <button
              type="button"
              className={`mic-btn ${isListening ? 'mic-btn-active' : ''}`}
              onClick={handleMicClick}
              disabled={isLoading}
              aria-label={isListening ? t.stopMic : t.startMic}
              title={isListening ? t.stopMic : t.startMic}
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M12 15a3 3 0 003-3V6a3 3 0 10-6 0v6a3 3 0 003 3z"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M19 11a7 7 0 01-14 0M12 18v3"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
          <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
            {t.send}
          </button>
        </form>
      </div>

      <p className="disclaimer">{t.disclaimer}</p>
    </div>
  )
}
