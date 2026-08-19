import React, { useState } from 'react'
import { gadSeverity, useLanguage } from '../i18n'

export default function Gad7Page() {
  const { t, isAr } = useLanguage()
  const [answers, setAnswers] = useState(Array(7).fill(null))
  const [result, setResult] = useState(null)
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
      document.getElementById(`gad7-q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const score = answers.reduce((sum, val) => sum + val, 0)
    const severity = gadSeverity(score, isAr)
    setResult({ score, severity })
    setValidationError('')
    setTimeout(() => {
      document.getElementById('gad7-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)
  }

  const handleReset = () => {
    setAnswers(Array(7).fill(null))
    setResult(null)
    setValidationError('')
  }

  return (
    <div className="phq9-page">
      <header className="page-header">
        <div>
          <h2 className="page-title">{t.gadTitle}</h2>
          <p className="page-subtitle">{t.gadSubtitle}</p>
        </div>
      </header>

      <div className="phq9-form">
        {t.gadItems.map((question, index) => (
          <article key={index} id={`gad7-q-${index}`} className="question-card">
            <h3 className="question-number">{t.question} {index + 1}</h3>
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
                    name={`gad7-q${index}`}
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
        <div id="gad7-result" className="result-card">
          <div className="result-score-row">
            <span className="result-label">{t.yourScore('GAD-7')}</span>
            <span className="result-score">
              {result.score} <span className="result-max">/ 21</span>
            </span>
          </div>
          <div className={`severity-badge ${result.severity.className}`}>
            {result.severity.label}
          </div>
          <p className="severity-meaning">{result.severity.meaning}</p>
          <p className="result-disclaimer">{t.screeningDisclaimer('GAD-7')}</p>
        </div>
      )}
    </div>
  )
}
