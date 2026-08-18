import React from 'react'

const EXAMPLE_QUESTIONS = [
  'What are the common symptoms of depression?',
  'What treatments are available for depression?',
  'What is the PHQ-9?',
  'How can I support someone experiencing depression?',
]

function SourceList({ sources }) {
  if (!sources?.length) return null

  return (
    <div className="sources-block">
      <h4 className="sources-title">Sources</h4>
      <ul className="sources-list">
        {sources.map((source, i) => (
          <li key={i} className="source-item">
            <span className="source-name">{source.name}</span>
            {source.relevance_score != null && (
              <span className="source-score">Relevance: {source.relevance_score.toFixed(2)}</span>
            )}
            {source.page != null && (
              <span className="source-page">p. {source.page}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="avatar assistant-avatar" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path
              d="M12 4c-2.8 0-4.8 2-4.8 4.8 0 3.2 2.4 4.4 4.8 7.2 2.4-2.8 4.8-4 4.8-7.2C16.8 6 14.8 4 12 4z"
              fill="currentColor"
            />
          </svg>
        </div>
      )}
      <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
        {message.loading ? (
          <div className="typing-indicator" aria-label="Loading response">
            <span /><span /><span />
          </div>
        ) : (
          <>
            <p className="message-text">{message.content}</p>
            {!isUser && message.sources && <SourceList sources={message.sources} />}
          </>
        )}
      </div>
    </div>
  )
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
        { role: 'assistant', content: data.answer, sources: data.sources },
      ])
    } catch (err) {
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
