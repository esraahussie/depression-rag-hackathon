import React, { useState } from 'react'

const GAD7_QUESTIONS = [
  'Feeling nervous, anxious, or on edge',
  'Not being able to stop or control worrying',
  'Worrying too much about different things',
  'Trouble relaxing',
  'Being so restless that it is hard to sit still',
  'Becoming easily annoyed or irritable',
  'Feeling afraid as if something awful might happen',
]

const OPTIONS = [
  { label: 'Not at all', value: 0 },
  { label: 'Several days', value: 1 },
  { label: 'More than half the days', value: 2 },
  { label: 'Nearly every day', value: 3 },
]

function getSeverity(score) {
  if (score <= 4) {
    return {
      label: 'Minimal',
      className: 'severity-minimal',
      meaning:
        'A score in this range suggests minimal or no significant anxiety symptoms. Occasional worry is common and does not necessarily require clinical intervention.',
    }
  }
  if (score <= 9) {
    return {
      label: 'Mild',
      className: 'severity-mild',
      meaning:
        'A score in this range suggests mild anxiety symptoms. Self-monitoring and stress-management strategies may help; consider a follow-up screen if symptoms persist or worsen.',
    }
  }
  if (score <= 14) {
    return {
      label: 'Moderate',
      className: 'severity-moderate',
      meaning:
        'A score in this range suggests moderate anxiety symptoms that may be starting to affect daily functioning. Discussing these results with a healthcare professional is recommended.',
    }
  }
  return {
    label: 'Severe',
    className: 'severity-severe',
    meaning:
      'A score in this range suggests severe anxiety symptoms. It is strongly recommended that you speak with a healthcare professional soon for a fuller evaluation.',
  }
}

export default function Gad7Page() {
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
      setValidationError(`Please answer question ${unanswered + 1} before calculating your score.`)
      document.getElementById(`gad7-q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const score = answers.reduce((sum, val) => sum + val, 0)
    const severity = getSeverity(score)

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
          <h2 className="page-title">GAD-7 Anxiety Screening</h2>
          <p className="page-subtitle">
            Over the last 2 weeks, how often have you been bothered by any of the following problems?
          </p>
        </div>
      </header>

      <div className="phq9-form">
        {GAD7_QUESTIONS.map((question, index) => (
          <article key={index} id={`gad7-q-${index}`} className="question-card">
            <h3 className="question-number">Question {index + 1}</h3>
            <p className="question-text">{question}</p>
            <fieldset className="options-group">
              <legend className="sr-only">Select frequency for question {index + 1}</legend>
              {OPTIONS.map((opt) => (
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
        <p className="validation-error" role="alert">
          {validationError}
        </p>
      )}

      <div className="phq9-actions">
        <button type="button" className="calculate-btn" onClick={handleCalculate}>
          Calculate Score
        </button>
        {result && (
          <button type="button" className="reset-btn" onClick={handleReset}>
            Start Over
          </button>
        )}
      </div>

      {result && (
        <div id="gad7-result" className="result-card">
          <div className="result-score-row">
            <span className="result-label">Your GAD-7 Score</span>
            <span className="result-score">
              {result.score} <span className="result-max">/ 21</span>
            </span>
          </div>
          <div className={`severity-badge ${result.severity.className}`}>
            {result.severity.label}
          </div>
          <div className="severity-scale">
            <div className="scale-bar">
              <span className="scale-segment minimal" title="0–4 Minimal" />
              <span className="scale-segment mild" title="5–9 Mild" />
              <span className="scale-segment moderate" title="10–14 Moderate" />
              <span className="scale-segment severe" title="15–21 Severe" />
              <span
                className="scale-marker"
                style={{ left: `${Math.min((result.score / 21) * 100, 100)}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="scale-labels">
              <span>Minimal</span>
              <span>Mild</span>
              <span>Moderate</span>
              <span>Severe</span>
            </div>
          </div>
          <p className="severity-meaning">{result.severity.meaning}</p>
          <p className="result-disclaimer">
            The GAD-7 is a screening tool and does not by itself provide a clinical diagnosis. Consider
            discussing your results with a qualified healthcare professional.
          </p>
        </div>
      )}
    </div>
  )
}