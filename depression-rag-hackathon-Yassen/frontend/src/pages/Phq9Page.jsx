import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { phqSeverity, useLanguage } from '../i18n'

export default function Phq9Page() {
  const { t, isAr } = useLanguage()
  const [answers, setAnswers] = useState(Array(9).fill(null))
  const [result, setResult] = useState(null)
  const [showCrisisAlert, setShowCrisisAlert] = useState(false)
  const [validationError, setValidationError] = useState('')
  const navigate = useNavigate()

  const handleChange = (questionIndex, value) => {
    const updated = [...answers]
    updated[questionIndex] = value
    setAnswers(updated)
    setValidationError('')
    if (result) setResult(null)
  }

  const handleCalculate = () => {
    const unanswered = answers.findIndex((a) => a === null)
    if (unanswered !== -1) {
      setValidationError(t.answerQuestion(unanswered + 1))
      document.getElementById(`q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const score = answers.reduce((sum, val) => sum + val, 0)
    const severity = phqSeverity(score, isAr)
    const q9Answer = answers[8]

    setShowCrisisAlert(q9Answer > 0)
    setResult({ score, severity })
    setValidationError('')

    setTimeout(() => {
      document.getElementById('phq9-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)
  }

  const handleReset = () => {
    setAnswers(Array(9).fill(null))
    setResult(null)
    setShowCrisisAlert(false)
    setValidationError('')
  }

  const handleAskChat = () => {
    if (!result) return
    const query = isAr
      ? `الإرشاد بيقول إيه لمريض نتيجة PHQ-9 عنده ${result.score} (${result.severity.label})؟`
      : `What does the guideline recommend for a patient with a PHQ-9 score of ${result.score} (${result.severity.label} depression)?`
    navigate('/chat', {
      state: {
        autoQuery: query,
        autoExplanation: result.severity.meaning,
        autoExplanationQuestion: isAr
          ? `معنى نتيجة PHQ-9 = ${result.score} (${result.severity.label}) إيه؟`
          : `What does a PHQ-9 score of ${result.score} (${result.severity.label} depression) mean?`,
      },
    })
  }

  return (
    <div className="phq9-page">
      <header className="page-header">
        <div>
          <h2 className="page-title">{t.phqTitle}</h2>
          <p className="page-subtitle">{t.phqSubtitle}</p>
        </div>
      </header>

      {showCrisisAlert && (
        <div className="crisis-alert" role="alert">
          <div className="crisis-alert-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <strong>{t.crisisTitle}</strong>
            <p>{t.crisisBody}</p>
            <p className="crisis-resources">{t.crisisResources}</p>
          </div>
        </div>
      )}

      <div className="phq9-form">
        {t.phqItems.map((question, index) => (
          <article key={index} id={`q-${index}`} className="question-card">
            <h3 className="question-number">
              {t.question} {index + 1}
              {index === 8 && <span className="question-sensitive"> · {t.sensitive}</span>}
            </h3>
            <p className="question-text">{question}</p>
            <fieldset className="options-group">
              <legend className="sr-only">{t.question} {index + 1}</legend>
              {t.phqOptions.map((opt) => (
                <label
                  key={opt.value}
                  className={`option-label ${answers[index] === opt.value ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name={`q${index}`}
                    value={opt.value}
                    checked={answers[index] === opt.value}
                    onChange={() => handleChange(index, opt.value)}
                  />
                  <span className="option-radio" aria-hidden="true" />
                  <span className="option-text">{opt.label}</span>
                  <span className="option-score">{opt.value}</span>
                </label>
              ))}
            </fieldset>
          </article>
        ))}
      </div>

      {validationError && (
        <p className="validation-error" role="alert">
          {validationError}
        </p>
      )}

      <div className="phq9-actions">
        <button type="button" className="calculate-btn" onClick={handleCalculate}>
          {t.calculate}
        </button>
        {result && (
          <button type="button" className="reset-btn" onClick={handleReset}>
            {t.startOver}
          </button>
        )}
      </div>

      {result && (
        <div id="phq9-result" className="result-card">
          <div className="result-score-row">
            <span className="result-label">{t.yourScore('PHQ-9')}</span>
            <span className="result-score">
              {result.score} <span className="result-max">/ 27</span>
            </span>
          </div>
          <div className={`severity-badge ${result.severity.className}`}>
            {result.severity.label}
          </div>
          <div className="severity-scale">
            <div className="scale-bar">
              <span className="scale-segment minimal" />
              <span className="scale-segment mild" />
              <span className="scale-segment moderate" />
              <span className="scale-segment mod-severe" />
              <span className="scale-segment severe" />
              <span
                className="scale-marker"
                style={{ insetInlineStart: `${Math.min((result.score / 27) * 100, 100)}%` }}
                aria-hidden="true"
              />
            </div>
          </div>
          <p className="severity-meaning">{result.severity.meaning}</p>
          <p className="result-disclaimer">{t.screeningDisclaimer('PHQ-9')}</p>
          <button type="button" className="ask-chat-btn" onClick={handleAskChat}>
            {t.askGuideline}
          </button>
        </div>
      )}
    </div>
  )
}
