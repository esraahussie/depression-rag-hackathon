const EXAMPLE_QUESTIONS = [
  'What are the common symptoms of depression?',
  'What treatments are available for depression?',
  'What is the PHQ-9?',
  'How can I support someone experiencing depression?',
]

const PHQ9_QUESTIONS = [
  'Little interest or pleasure in doing things',
  'Feeling down, depressed, or hopeless',
  'Trouble falling or staying asleep, or sleeping too much',
  'Feeling tired or having little energy',
  'Poor appetite or overeating',
  'Feeling bad about yourself — or that you are a failure or have let yourself or your family down',
  'Trouble concentrating on things, such as reading the newspaper or watching television',
  'Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual',
  'Thoughts that you would be better off dead or of hurting yourself in some way',
]

const PHQ9_OPTIONS = [
  { label: 'Not at all', value: 0 },
  { label: 'Several days', value: 1 },
  { label: 'More than half the days', value: 2 },
  { label: 'Nearly every day', value: 3 },
]

const chatState = { messages: [], isLoading: false }
const phq9State = { answers: Array(9).fill(null), result: null, showCrisis: false, error: '' }

function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function getSeverity(score) {
  if (score <= 4) return { label: 'Minimal', className: 'severity-minimal' }
  if (score <= 9) return { label: 'Mild', className: 'severity-mild' }
  if (score <= 14) return { label: 'Moderate', className: 'severity-moderate' }
  if (score <= 19) return { label: 'Moderately severe', className: 'severity-mod-severe' }
  return { label: 'Severe', className: 'severity-severe' }
}

function formatRelevance(score) {
  if (score == null) return null
  return `${Math.round(score * 100)}%`
}

function renderAnswerWithCitations(text) {
  if (!text) return ''
  return text.split(/(\[\d+\])/g).map((part) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (match) {
      const id = match[1]
      return `<button type="button" class="citation-marker" data-citation="${id}" aria-label="Go to source ${id}">[${id}]</button>`
    }
    return escapeHtml(part)
  }).join('')
}

function renderSourceCard(source, prefix = '') {
  const page = source.page != null ? source.page : 'N/A'
  const chunk = source.chunk != null ? source.chunk : 'N/A'
  const relevance = formatRelevance(source.relevance_score)
  const relHtml = relevance ? `<div><dt>Relevance</dt><dd>${relevance}</dd></div>` : ''
  const url = source.source_url || ''
  const nameHtml = url
    ? `<a class="source-name source-name-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.name)}</a>`
    : `<span class="source-name">${escapeHtml(source.name)}</span>`
  const urlHtml = url
    ? `<a class="source-url" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open guideline</a>`
    : ''
  return `
    <li id="source-${source.citation_id}" class="source-item">
      <div class="source-header">
        <span class="source-citation-id">[${source.citation_id}]</span>
        ${nameHtml}
      </div>
      ${urlHtml}
      <dl class="source-meta">
        <div><dt>PDF</dt><dd>${escapeHtml(source.pdf)}</dd></div>
        <div><dt>Page</dt><dd>${page}</dd></div>
        <div><dt>Chunk</dt><dd>${chunk}</dd></div>
        ${relHtml}
      </dl>
    </li>`
}

function renderSources(sources, additionalSources, confidence, status) {
  let html = ''
  if (confidence != null && status !== 'out_of_scope') {
    html += `<p class="confidence-badge">Confidence: <strong>${Math.round(confidence * 100)}%</strong></p>`
  }
  if (sources?.length) {
    html += `<div class="sources-block"><h4 class="sources-title">Supporting Sources</h4><ul class="sources-list">${sources.map((s) => renderSourceCard(s)).join('')}</ul></div>`
  }
  if (additionalSources?.length) {
    html += `<div class="sources-block sources-additional"><h4 class="sources-title">Additional Retrieved Sources</h4><ul class="sources-list">${additionalSources.map((s) => renderSourceCard(s)).join('')}</ul></div>`
  }
  return html
}

function renderChatMessage(msg) {
  if (msg.role === 'user') {
    return `
      <div class="message-row user">
        <div class="message-bubble user-bubble">
          <p class="message-text">${escapeHtml(msg.content)}</p>
        </div>
      </div>`
  }

  if (msg.loading) {
    return `
      <div class="message-row assistant">
        <div class="avatar assistant-avatar">
          <svg viewBox="0 0 24 24" fill="none"><path d="M12 4c-2.8 0-4.8 2-4.8 4.8 0 3.2 2.4 4.4 4.8 7.2 2.4-2.8 4.8-4 4.8-7.2C16.8 6 14.8 4 12 4z" fill="currentColor"/></svg>
        </div>
        <div class="message-bubble assistant-bubble">
          <div class="typing-indicator" aria-label="Loading response"><span></span><span></span><span></span></div>
        </div>
      </div>`
  }

  return `
    <div class="message-row assistant">
      <div class="avatar assistant-avatar">
        <svg viewBox="0 0 24 24" fill="none"><path d="M12 4c-2.8 0-4.8 2-4.8 4.8 0 3.2 2.4 4.4 4.8 7.2 2.4-2.8 4.8-4 4.8-7.2C16.8 6 14.8 4 12 4z" fill="currentColor"/></svg>
      </div>
      <div class="message-bubble assistant-bubble">
        <p class="message-text">${renderAnswerWithCitations(msg.content)}</p>
        ${renderSources(msg.sources, msg.additionalSources, msg.confidence, msg.status)}
      </div>
    </div>`
}

function renderChatPage() {
  const empty = chatState.messages.length === 0
  const messagesHtml = empty
    ? `
      <div class="chat-empty">
        <div class="empty-icon" aria-hidden="true">
          <svg viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="22" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
            <path d="M16 22c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M24 30v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <h3>How can I help you today?</h3>
        <p>Ask about depression symptoms, treatments, screening, or how to support others.</p>
        <div class="example-questions">
          ${EXAMPLE_QUESTIONS.map((q) => `<button type="button" class="example-btn" data-question="${escapeHtml(q)}" ${chatState.isLoading ? 'disabled' : ''}>${escapeHtml(q)}</button>`).join('')}
        </div>
      </div>`
    : chatState.messages.map(renderChatMessage).join('')

  return `
    <div class="chat-page">
      <header class="page-header">
        <div>
          <h2 class="page-title">Depression Assistant</h2>
          <p class="page-subtitle">Evidence-based depression information and support.</p>
        </div>
      </header>
      <div class="chat-container">
        <div class="chat-messages" role="log" aria-live="polite" aria-label="Chat messages">
          ${messagesHtml}
          <div id="chat-end"></div>
        </div>
        <form class="chat-input-bar" id="chat-form">
          <input type="text" class="chat-input" id="chat-input" placeholder="Ask a question about depression..." ${chatState.isLoading ? 'disabled' : ''} aria-label="Your message" />
          <button type="submit" class="send-btn" id="send-btn" ${chatState.isLoading ? 'disabled' : ''}>Send</button>
        </form>
      </div>
      <p class="disclaimer">This assistant provides educational information and is not a substitute for professional medical advice.</p>
    </div>`
}

function renderPhq9Page() {
  const crisisHtml = phq9State.showCrisis ? `
    <div class="crisis-alert" role="alert">
      <div class="crisis-alert-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <strong>Your safety matters.</strong>
        <p>You indicated having thoughts of self-harm. Please reach out to a mental health professional, a trusted person, or emergency services immediately if you are in danger.</p>
        <p class="crisis-resources">In the U.S., call or text <strong>988</strong> (Suicide & Crisis Lifeline). If you are in immediate danger, call <strong>911</strong> or go to your nearest emergency room.</p>
      </div>
    </div>` : ''

  const questionsHtml = PHQ9_QUESTIONS.map((q, i) => `
    <article class="question-card" id="q-${i}">
      <h3 class="question-number">Question ${i + 1}${i === 8 ? ' <span class="question-sensitive">· Sensitive</span>' : ''}</h3>
      <p class="question-text">${escapeHtml(q)}</p>
      <fieldset class="options-group">
        <legend class="sr-only">Select frequency for question ${i + 1}</legend>
        ${PHQ9_OPTIONS.map((opt) => `
          <label class="option-label ${phq9State.answers[i] === opt.value ? 'selected' : ''}">
            <input type="radio" name="q${i}" value="${opt.value}" ${phq9State.answers[i] === opt.value ? 'checked' : ''} data-q="${i}" />
            <span class="option-radio" aria-hidden="true"></span>
            <span class="option-text">${opt.label}</span>
            <span class="option-score">${opt.value}</span>
          </label>`).join('')}
      </fieldset>
    </article>`).join('')

  const resultHtml = phq9State.result ? (() => {
    const { score, severity } = phq9State.result
    const markerPos = Math.min((score / 27) * 100, 100)
    return `
      <div id="phq9-result" class="result-card">
        <div class="result-score-row">
          <span class="result-label">Your PHQ-9 Score</span>
          <span class="result-score">${score} <span class="result-max">/ 27</span></span>
        </div>
        <div class="severity-badge ${severity.className}">${severity.label}</div>
        <div class="severity-scale">
          <div class="scale-bar">
            <span class="scale-segment minimal" title="0–4 Minimal"></span>
            <span class="scale-segment mild" title="5–9 Mild"></span>
            <span class="scale-segment moderate" title="10–14 Moderate"></span>
            <span class="scale-segment mod-severe" title="15–19 Moderately severe"></span>
            <span class="scale-segment severe" title="20–27 Severe"></span>
            <span class="scale-marker" style="left: ${markerPos}%"></span>
          </div>
          <div class="scale-labels">
            <span>Minimal</span><span>Mild</span><span>Moderate</span><span>Mod. Severe</span><span>Severe</span>
          </div>
        </div>
        <p class="result-disclaimer">The PHQ-9 is a screening tool and does not by itself provide a clinical diagnosis. Consider discussing your results with a qualified healthcare professional.</p>
      </div>`
  })() : ''

  return `
    <div class="phq9-page">
      <header class="page-header">
        <div>
          <h2 class="page-title">PHQ-9 Depression Screening</h2>
          <p class="page-subtitle">Over the last 2 weeks, how often have you been bothered by any of the following problems?</p>
        </div>
      </header>
      ${crisisHtml}
      <div class="phq9-form">${questionsHtml}</div>
      ${phq9State.error ? `<p class="validation-error" role="alert">${escapeHtml(phq9State.error)}</p>` : ''}
      <div class="phq9-actions">
        <button type="button" class="calculate-btn" id="calculate-btn">Calculate Score</button>
        ${phq9State.result ? '<button type="button" class="reset-btn" id="reset-btn">Start Over</button>' : ''}
      </div>
      ${resultHtml}
    </div>`
}

function getRoute() {
  const hash = location.hash.slice(1) || '/chat'
  return hash.startsWith('/phq9') ? 'phq9' : 'chat'
}

function updateNav(route) {
  document.querySelectorAll('[data-route]').forEach((el) => {
    el.classList.toggle('active', el.dataset.route === route)
  })
}

function render() {
  const route = getRoute()
  updateNav(route)
  const root = document.getElementById('app-root')
  root.innerHTML = route === 'phq9' ? renderPhq9Page() : renderChatPage()
  bindEvents(route)
}

async function sendMessage(text) {
  const trimmed = text.trim()
  if (!trimmed || chatState.isLoading) return

  chatState.messages.push({ role: 'user', content: trimmed })
  chatState.messages.push({ role: 'assistant', content: '', loading: true })
  chatState.isLoading = true
  render()
  scrollChatToBottom()

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
    chatState.messages.pop()
    chatState.messages.push({ role: 'assistant', content: data.answer, sources: data.sources, additionalSources: data.additional_sources, confidence: data.confidence, status: data.status })
  } catch {
    chatState.messages.pop()
    chatState.messages.push({
      role: 'assistant',
      content: 'Sorry, I could not process your request right now. Please ensure the backend server is running and try again.',
    })
  } finally {
    chatState.isLoading = false
    render()
    scrollChatToBottom()
    document.getElementById('chat-input')?.focus()
  }
}

function scrollChatToBottom() {
  requestAnimationFrame(() => {
    document.getElementById('chat-end')?.scrollIntoView({ behavior: 'smooth' })
  })
}

function bindEvents(route) {
  if (route === 'chat') {
    document.getElementById('chat-form')?.addEventListener('submit', (e) => {
      e.preventDefault()
      const input = document.getElementById('chat-input')
      const text = input.value
      input.value = ''
      sendMessage(text)
    })
    document.querySelectorAll('.example-btn').forEach((btn) => {
      btn.addEventListener('click', () => sendMessage(btn.dataset.question))
    })
    document.querySelectorAll('.citation-marker').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.citation
        const el = document.getElementById(`source-${id}`)
        el?.classList.add('source-highlight')
        el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        setTimeout(() => el?.classList.remove('source-highlight'), 2000)
      })
    })
  } else {
    document.querySelectorAll('.option-label input').forEach((input) => {
      input.addEventListener('change', () => {
        const idx = parseInt(input.dataset.q, 10)
        phq9State.answers[idx] = parseInt(input.value, 10)
        phq9State.error = ''
        phq9State.result = null
        render()
      })
    })
    document.getElementById('calculate-btn')?.addEventListener('click', () => {
      const unanswered = phq9State.answers.findIndex((a) => a === null)
      if (unanswered !== -1) {
        phq9State.error = `Please answer question ${unanswered + 1} before calculating your score.`
        render()
        document.getElementById(`q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        return
      }
      const score = phq9State.answers.reduce((s, v) => s + v, 0)
      phq9State.result = { score, severity: getSeverity(score) }
      phq9State.showCrisis = phq9State.answers[8] > 0
      phq9State.error = ''
      render()
      setTimeout(() => document.getElementById('phq9-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    })
    document.getElementById('reset-btn')?.addEventListener('click', () => {
      phq9State.answers = Array(9).fill(null)
      phq9State.result = null
      phq9State.showCrisis = false
      phq9State.error = ''
      render()
    })
  }
}

window.addEventListener('hashchange', render)
if (!location.hash) location.hash = '#/chat'
render()
