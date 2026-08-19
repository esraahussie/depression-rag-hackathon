import React, { useState } from 'react'
import { epdsSeverity, useLanguage } from '../i18n'

export default function EpdsPage() {
  const { t, isAr } = useLanguage()
  const [answers, setAnswers] = useState(Array(10).fill(null))
  const [result, setResult] = useState(null)
  const [showCrisisAlert, setShowCrisisAlert] = useState(false)
  const [validationError, setValidationError] = useState('')

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
      document.getElementById(`epds-q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const score = answers.reduce((sum, val) => sum + val, 0)
    const severity = epdsSeverity(score, isAr)
    setShowCrisisAlert(answers[9] > 0)
    setResult({ score, severity })
    setValidationError('')
    setTimeout(() => {
      document.getElementById('epds-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)
  }

  const handleReset = () => {
    setAnswers(Array(10).fill(null))
    setResult(null)
    setShowCrisisAlert(false)
    setValidationError('')
  }

  return (
    <div className="phq9-page">
      <header className="page-header">
        <div>
          <h2 className="page-title">{t.epdsTitle}</h2>
          <p className="page-subtitle">{t.epdsSubtitle}</p>
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
        {t.epdsItems.map((question, index) => (
          <article key={index} id={`epds-q-${index}`} className="question-card">
            <h3 className="question-number">
              {t.question} {index + 1}
              {index === 9 && <span className="question-sensitive"> · {t.sensitive}</span>}
            </h3>
            <p className="question-text">{question.text}</p>
            <fieldset className="options-group">
              <legend className="sr-only">{t.question} {index + 1}</legend>
              {question.options.map((opt) => (
                <label
                  key={opt.value}
                  className={`option-label ${answers[index] === opt.value ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name={`epds-q${index}`}
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
        <p className="validation-error" role="alert">{validationError}</p>
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
        <div id="epds-result" className="result-card">
          <div className="result-score-row">
            <span className="result-label">{t.yourScore('EPDS')}</span>
            <span className="result-score">
              {result.score} <span className="result-max">/ 30</span>
            </span>
          </div>
          <div className={`severity-badge ${result.severity.className}`}>
            {result.severity.label}
          </div>
          <p className="severity-meaning">{result.severity.meaning}</p>
          <p className="result-disclaimer">{t.screeningDisclaimer('EPDS')}</p>
        </div>
      )}
    </div>
  )
}
