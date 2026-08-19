import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
        'A score in this range suggests minimal or no significant depressive symptoms. Occasional low mood is common and does not necessarily require clinical intervention.',
    }
  }
  if (score <= 9) {
    return {
      label: 'Mild',
      className: 'severity-mild',
      meaning:
        'A score in this range suggests mild depressive symptoms. Self-monitoring, healthy routines, and social support may help; consider a follow-up screen if symptoms persist or worsen.',
    }
  }
  if (score <= 14) {
    return {
      label: 'Moderate',
      className: 'severity-moderate',
      meaning:
        'A score in this range suggests moderate depressive symptoms that may be affecting daily functioning. Discussing these results with a healthcare professional is recommended.',
    }
  }
  if (score <= 19) {
    return {
      label: 'Moderately severe',
      className: 'severity-mod-severe',
      meaning:
        'A score in this range suggests moderately severe depressive symptoms. A timely conversation with a healthcare professional is recommended to discuss treatment options.',
    }
  }
  return {
    label: 'Severe',
    className: 'severity-severe',
    meaning:
      'A score in this range suggests severe depressive symptoms. It is strongly recommended that you speak with a healthcare professional soon for a fuller evaluation.',
  }
}

export default function Phq9Page() {
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
      setValidationError(`Please answer question ${unanswered + 1} before calculating your score.`)
      document.getElementById(`q-${unanswered}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }

    const score = answers.reduce((sum, val) => sum + val, 0)
    const severity = getSeverity(score)
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
    const query = `What does the guideline recommend for a patient with a PHQ-9 score of ${result.score} (${result.severity.label} depression)?`
    navigate('/chat', {
      state: {
        autoQuery: query,
        autoExplanation: result.severity.meaning,
        autoExplanationQuestion: `What does a PHQ-9 score of ${result.score} (${result.severity.label} depression) mean?`,
      },
    })
  }

  return (
    <div className="phq9-page">
      <header className="page-header">
        <div>
          <h2 className="page-title">PHQ-9 Depression Screening</h2>
          <p className="page-subtitle">
            Over the last 2 weeks, how often have you been bothered by any of the following problems?
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
        {PHQ9_QUESTIONS.map((question, index) => (
          <article key={index} id={`q-${index}`} className="question-card">
            <h3 className="question-number">
              Question {index + 1}
              {index === 8 && <span className="question-sensitive"> · Sensitive</span>}
            </h3>
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
          Calculate Score
        </button>
        {result && (
          <button type="button" className="reset-btn" onClick={handleReset}>
            Start Over
          </button>
        )}
      </div>

      {result && (
        <div id="phq9-result" className="result-card">
          <div className="result-score-row">
            <span className="result-label">Your PHQ-9 Score</span>
            <span className="result-score">
              {result.score} <span className="result-max">/ 27</span>
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
              <span className="scale-segment mod-severe" title="15–19 Moderately severe" />
              <span className="scale-segment severe" title="20–27 Severe" />
              <span
                className="scale-marker"
                style={{ left: `${Math.min((result.score / 27) * 100, 100)}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="scale-labels">
              <span>Minimal</span>
              <span>Mild</span>
              <span>Moderate</span>
              <span>Mod. Severe</span>
              <span>Severe</span>
            </div>
          </div>
          <p className="severity-meaning">{result.severity.meaning}</p>
          <p className="result-disclaimer">
            The PHQ-9 is a screening tool and does not by itself provide a clinical diagnosis. Consider
            discussing your results with a qualified healthcare professional.
          </p>
          <button type="button" className="ask-chat-btn" onClick={handleAskChat}>
            Ask the guideline about this score
          </button>
        </div>
      )}
    </div>
  )
}