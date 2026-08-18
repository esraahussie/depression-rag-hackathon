import React from 'react'

const EXAMPLE_QUESTIONS = [
  'What are the common symptoms of depression?',
  'What treatments are available for depression?',
  'What is the PHQ-9?',
  'How can I support someone experiencing depression?',
]

function formatRelevance(score) {
  if (score == null) return null
  return `${Math.round(score * 100)}%`
}

function renderAnswerWithCitations(text, onCitationClick) {
  if (!text) return null
  const parts = text.split(/(\[\d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (match) {
      const id = match[1]
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
    return <React.Fragment key={`t-${i}`}>{part}</React.Fragment>
  })
}

function SourceCard({ source, highlighted }) {
  const page = source.page != null ? source.page : 'N/A'
  const chunk = source.chunk != null ? source.chunk : 'N/A'
  const relevance = formatRelevance(source.relevance_score)

  return (
    <li
      id={`source-${source.citation_id}`}
      className={`source-item ${highlighted ? 'source-highlight' : ''}`}
    >
      <div className="source-header">
        <span className="source-citation-id">[{source.citation_id}]</span>
        <span className="source-name">{source.name}</span>
      </div>
      <dl className="source-meta">
        <div><dt>PDF</dt><dd>{source.pdf}</dd></div>
        <div><dt>Page</dt><dd>{page}</dd></div>
        <div><dt>Chunk</dt><dd>{chunk}</dd></div>
        {relevance != null && (
          <div><dt>Relevance</dt><dd>{relevance}</dd></div>
        )}
      </dl>
    </li>
  )
}

function AssistantMessage({ message }) {
  const [highlightedId, setHighlightedId] = React.useState(null)

  const handleCitationClick = (id) => {
    setHighlightedId(id)
    document.getElementById(`source-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    setTimeout(() => setHighlightedId(null), 2000)
  }

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
      <div className="message-bubble assistant-bubble">
        {message.loading ? (
          <div className="typing-indicator" aria-label="Loading response">
            <span /><span /><span />
          </div>
        ) : (
          <>
            <p className="message-text">
              {renderAnswerWithCitations(message.content, handleCitationClick)}
            </p>
            {confidencePct != null && message.status !== 'out_of_scope' && (
              <p className="confidence-badge" aria-label={`Confidence ${confidencePct}`}>
                Confidence: <strong>{confidencePct}</strong>
              </p>
            )}
            {message.sources?.length > 0 && (
              <div className="sources-block">
                <h4 className="sources-title">Supporting Sources</h4>
                <ul className="sources-list">
                  {message.sources.map((source) => (
                    <SourceCard
                      key={source.citation_id}
                      source={source}
                      highlighted={String(highlightedId) === String(source.citation_id)}
                    />
                  ))}
                </ul>
              </div>
            )}
            {message.additionalSources?.length > 0 && (
              <div className="sources-block sources-additional">
                <h4 className="sources-title">Additional Retrieved Sources</h4>
                <ul className="sources-list">
                  {message.additionalSources.map((source) => (
                    <SourceCard key={`add-${source.citation_id}`} source={source} highlighted={false} />
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function MessageBubble({ message }) {
  if (message.role === 'user') {
    return (
      <div className="message-row user">
        <div className="message-bubble user-bubble">
          <p className="message-text">{message.content}</p>
        </div>
      </div>
    )
  }
  return <AssistantMessage message={message} />
}

export default function ChatPage() {
  const [messages, setMessages] = React.useState([])
  const [input, setInput] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const chatEndRef = React.useRef(null)
  const inputRef = React.useRef(null)

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    const userMessage = { role: 'user', content: trimmed }
    const loadingMessage = { role: 'assistant', content: '', loading: true }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setInput('')
    setIsLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to get a response')
      }

      const data = await res.json()
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          additionalSources: data.additional_sources,
          confidence: data.confidence,
          status: data.status,
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          content:
            'Sorry, I could not process your request right now. Please ensure the backend server is running and try again.',
        },
      ])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="chat-page">
      <header className="page-header">
        <div>
          <h2 className="page-title">Depression Assistant</h2>
          <p className="page-subtitle">Evidence-based depression information and support.</p>
        </div>
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
              <h3>How can I help you today?</h3>
              <p>Ask about depression symptoms, treatments, screening, or how to support others.</p>
              <div className="example-questions">
                {EXAMPLE_QUESTIONS.map((q) => (
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
            messages.map((msg, i) => <MessageBubble key={i} message={msg} />)
          )}
          <div ref={chatEndRef} />
        </div>

        <form className="chat-input-bar" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Ask a question about depression..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            aria-label="Your message"
          />
          <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
            Send
          </button>
        </form>
      </div>

      <p className="disclaimer">
        This assistant provides educational information and is not a substitute for professional medical advice.
      </p>
    </div>
  )
}
