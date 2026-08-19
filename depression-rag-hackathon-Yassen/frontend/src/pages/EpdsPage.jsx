import React, { useState } from 'react'

const EPDS_QUESTIONS = [
  {
    text: 'I have been able to laugh and see the funny side of things',
    options: [
      { label: 'As much as I always could', value: 0 },
      { label: 'Not quite so much now', value: 1 },
      { label: 'Definitely not so much now', value: 2 },
      { label: 'Not at all', value: 3 },
    ],
  },
  {
    text: 'I have looked forward with enjoyment to things',
    options: [
      { label: 'As much as I ever did', value: 0 },
      { label: 'Rather less than I used to', value: 1 },
      { label: 'Definitely less than I used to', value: 2 },
      { label: 'Hardly at all', value: 3 },
    ],
  },
  {
    text: 'I have blamed myself unnecessarily when things went wrong',
    options: [
      { label: 'No, never', value: 0 },
      { label: 'Not very often', value: 1 },
      { label: 'Yes, some of the time', value: 2 },
      { label: 'Yes, most of the time', value: 3 },
    ],
  },
  {
    text: 'I have been anxious or worried for no good reason',
    options: [
      { label: 'No, not at all', value: 0 },
      { label: 'Hardly ever', value: 1 },
      { label: 'Yes, sometimes', value: 2 },
      { label: 'Yes, very often', value: 3 },
    ],
  },
  {
    text: 'I have felt scared or panicky for no very good reason',
    options: [
      { label: 'No, not at all', value: 0 },
      { label: 'No, not much', value: 1 },
      { label: 'Yes, sometimes', value: 2 },
      { label: 'Yes, quite a lot', value: 3 },
    ],
  },
  {
    text: 'Things have been getting on top of me',
    options: [
      { label: 'No, I have been coping as well as ever', value: 0 },
      { label: 'No, most of the time I have coped quite well', value: 1 },
      { label: "Yes, sometimes I haven't been coping as well as usual", value: 2 },
      { label: "Yes, most of the time I haven't been able to cope at all", value: 3 },
    ],
  },
  {
    text: 'I have been so unhappy that I have had difficulty sleeping',
    options: [
      { label: 'No, not at all', value: 0 },
      { label: 'Not very often', value: 1 },
      { label: 'Yes, sometimes', value: 2 },
      { label: 'Yes, most of the time', value: 3 },
    ],
  },
  {
    text: 'I have felt sad or miserable',
    options: [
      { label: 'No, not at all', value: 0 },
      { label: 'Not very often', value: 1 },
      { label: 'Yes, quite often', value: 2 },
      { label: 'Yes, most of the time', value: 3 },
    ],
  },
  {
    text: 'I have been so unhappy that I have been crying',
    options: [
      { label: 'No, never', value: 0 },
      { label: 'Only occasionally', value: 1 },
      { label: 'Yes, quite often', value: 2 },
      { label: 'Yes, most of the time', value: 3 },
    ],
  },
  {
    text: 'The thought of harming myself has occurred to me',
    options: [
      { label: 'Never', value: 0 },
      { label: 'Hardly ever', value: 1 },
      { label: 'Sometimes', value: 2 },
      { label: 'Yes, quite often', value: 3 },
    ],
  },
]

function getSeverity(score) {
  if (score <= 8) {
    return {
      label: 'Low likelihood',
      className: 'severity-minimal',
      meaning:
        'A score in this range suggests a low likelihood of postnatal depression. Occasional low mood or fatigue is common in the postpartum period.',
    }
  }
  if (score <= 11) {
    return {
      label: 'Possible — monitor',
      className: 'severity-mild',
      meaning:
        'A score in this range suggests some depressive symptoms may be present. Monitoring how you feel over the next couple of weeks and talking with your midwife, health visitor, or GP is a reasonable next step.',
    }
  }
  if (score <= 13) {
    return {
      label: 'Fairly high likelihood',
      className: 'severity-moderate',
      meaning:
        'A score in this range suggests a fairly high likelihood of postnatal depression. A follow-up conversation with a healthcare professional is recommended.',
    }
  }
  return {
    label: 'High likelihood',
    className: 'severity-severe',
    meaning:
      'A score in this range suggests a high likelihood of postnatal depression. It is strongly recommended that you speak with a healthcare professional soon for a fuller assessment.',
  }
}

export default function EpdsPage() {
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
      setValidationError(`Please answer question ${unanswered + 1} before calculating your score.`)
      document.getElementById(`epds-q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const score = answers.reduce((sum, val) => sum + val, 0)
    const severity = getSeverity(score)
    const q10Answer = answers[9]

    setShowCrisisAlert(q10Answer > 0)
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
          <h2 className="page-title">EPDS Postnatal Depression Screening</h2>
          <p className="page-subtitle">
            As you are pregnant or have recently had a baby, tell us how you have felt over the past 7 days,
            not just how you feel today.
          </p>
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
            <strong>Your safety matters.</strong>
            <p>
              You indicated having thoughts of self-harm. Please reach out to a mental health professional,
              a trusted person, or emergency services immediately if you are in danger.
            </p>
            <p className="crisis-resources">
              In the U.S., call or text <strong>988</strong> (Suicide & Crisis Lifeline). If you are in immediate
              danger, call <strong>911</strong> or go to your nearest emergency room.
            </p>
          </div>
        </div>
      )}

      <div className="phq9-form">
        {EPDS_QUESTIONS.map((question, index) => (
          <article key={index} id={`epds-q-${index}`} className="question-card">
            <h3 className="question-number">
              Question {index + 1}
              {index === 9 && <span className="question-sensitive"> · Sensitive</span>}
            </h3>
            <p className="question-text">{question.text}</p>
            <fieldset className="options-group">
              <legend className="sr-only">Select response for question {index + 1}</legend>
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
        <div id="epds-result" className="result-card">
          <div className="result-score-row">
            <span className="result-label">Your EPDS Score</span>
            <span className="result-score">
              {result.score} <span className="result-max">/ 30</span>
            </span>
          </div>
          <div className={`severity-badge ${result.severity.className}`}>
            {result.severity.label}
          </div>
          <div className="severity-scale">
            <div className="scale-bar">
              <span className="scale-segment minimal" title="0–8 Low likelihood" />
              <span className="scale-segment mild" title="9–11 Possible" />
              <span className="scale-segment moderate" title="12–13 Fairly high likelihood" />
              <span className="scale-segment severe" title="14–30 High likelihood" />
              <span
                className="scale-marker"
                style={{ left: `${Math.min((result.score / 30) * 100, 100)}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="scale-labels">
              <span>Low</span>
              <span>Possible</span>
              <span>Fairly high</span>
              <span>High</span>
            </div>
          </div>
          <p className="severity-meaning">{result.severity.meaning}</p>
          <p className="result-disclaimer">
            The EPDS is a screening tool and does not by itself provide a clinical diagnosis. A score above
            the threshold suggests the need for a fuller clinical assessment. Please discuss your results
            with a qualified healthcare professional.
          </p>
        </div>
      )}
    </div>
  )
}