import React from 'react'
import { useLanguage } from './i18n'

const STORAGE_KEY = 'mindcare-chat-messages'
const ChatContext = React.createContext(null)

function loadMessages() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((m) => m && !m.loading) : []
  } catch {
    return []
  }
}

function nextId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function ChatProvider({ children }) {
  const { t, lang } = useLanguage()
  const [messages, setMessages] = React.useState(loadMessages)
  const [autoSpeak, setAutoSpeak] = React.useState(false)
  const [pendingSpeakId, setPendingSpeakId] = React.useState(null)
  const [isLoading, setIsLoading] = React.useState(false)
  const loadingRef = React.useRef(false)
  const autoSpeakRef = React.useRef(false)

  React.useEffect(() => {
    autoSpeakRef.current = autoSpeak
  }, [autoSpeak])

  React.useEffect(() => {
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(messages.filter((m) => !m.loading)),
      )
    } catch {
      /* ignore quota / private mode */
    }
  }, [messages])

  const sendMessage = React.useCallback(async (text) => {
    const trimmed = text.trim()
    if (!trimmed || loadingRef.current) return

    const userMessage = { id: nextId(), role: 'user', content: trimmed }
    const loadingMessage = { id: nextId(), role: 'assistant', content: '', loading: true }

    loadingRef.current = true
    setIsLoading(true)
    setMessages((prev) => [...prev, userMessage, loadingMessage])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, language: lang }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to get a response')
      }

      const data = await res.json()
      const assistantId = nextId()
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          id: assistantId,
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          additionalSources: data.additional_sources,
          confidence: data.confidence,
          status: data.status,
        },
      ])
      if (autoSpeakRef.current) setPendingSpeakId(assistantId)
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          id: nextId(),
          role: 'assistant',
          content: t.error,
        },
      ])
    } finally {
      loadingRef.current = false
      setIsLoading(false)
    }
  }, [lang, t.error])

  const appendLocalExchange = React.useCallback((userContent, assistantContent) => {
    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: 'user', content: userContent },
      {
        id: nextId(),
        role: 'assistant',
        content: assistantContent,
        confidence: null,
        sources: [],
      },
    ])
  }, [])

  const value = React.useMemo(
    () => ({
      messages,
      setMessages,
      autoSpeak,
      setAutoSpeak,
      pendingSpeakId,
      setPendingSpeakId,
      isLoading,
      sendMessage,
      appendLocalExchange,
    }),
    [messages, autoSpeak, pendingSpeakId, isLoading, sendMessage, appendLocalExchange],
  )

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = React.useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used inside ChatProvider')
  return ctx
}
