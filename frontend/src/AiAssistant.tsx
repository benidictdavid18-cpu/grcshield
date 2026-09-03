/* The assistant's user interface: one panel, reused everywhere.
 *
 * Two design constraints, and they pull against each other.
 *
 * It must not dominate. The register, the Statement of Applicability and the workpapers
 * are the application; the assistant is a drawer inside them. So it is a collapsed panel
 * with a button row, in the same surface colours as everything else, and it renders
 * nothing at all until somebody asks it something.
 *
 * It must never be mistaken for a record. Everything it produces sits inside a panel
 * with a standing advisory label, above the list of what the model was actually shown,
 * and beneath a footer naming the model and the logged interaction. A suggestion styled
 * like a field is a suggestion somebody will eventually read as a field.
 */

import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { AiRequestError, aiApi, type AiEnvelope, type AiStatus } from './ai'

/* --- Status ------------------------------------------------------------------- */

/** The masthead chip.
 *
 *  Probed once per mount and answered from a server-side cache, because this renders on
 *  every page and polling a model server for a status light would be self-inflicted
 *  load. When the assistant is unavailable the chip says so *and* says that the rest of
 *  the application is not affected, which is the only part of the message that matters
 *  to somebody who came here to do GRC work.
 */
export function AiStatusChip() {
  const [status, setStatus] = useState<AiStatus | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    aiApi
      .status()
      .then((data) => {
        if (!cancelled) setStatus(data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (failed) return null
  if (!status) return null

  const state = !status.enabled ? 'off' : status.ready ? 'on' : 'degraded'
  const label = !status.enabled
    ? 'AI: disabled'
    : status.ready
      ? 'AI: connected'
      : status.reachable
        ? 'AI: model unavailable'
        : 'AI: offline'

  return (
    <span className={`ai-chip ai-chip-${state}`} title={status.detail}>
      <span className="ai-dot" aria-hidden="true" />
      {label}
      {status.enabled && status.ready && (
        <span className="ai-chip-model">{status.configured_model}</span>
      )}
    </span>
  )
}

/* --- The panel ----------------------------------------------------------------- */

export interface AiAction {
  key: string
  label: string
  hint?: string
  run: (question: string) => Promise<AiEnvelope>
  render: (data: AiEnvelope) => ReactNode
}

interface AiAssistantProps {
  title: string
  lede: string
  actions: AiAction[]
  /** Offer the free-text box. Bounded server-side; it is a question about the record,
   *  not a way to supply instructions. */
  allowQuestion?: boolean
  /** Task-specific inputs, rendered above the action row. Used where the assistant is
   *  not working from a record that is already on screen -- policy drafting has to ask
   *  what document and what topic. The parent owns that state, so this panel stays
   *  ignorant of any particular task. */
  extras?: ReactNode
}

export function AiAssistant({
  title,
  lede,
  actions,
  allowQuestion = true,
  extras,
}: AiAssistantProps) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<AiAction | null>(null)
  const [question, setQuestion] = useState('')
  const [data, setData] = useState<AiEnvelope | null>(null)
  const [error, setError] = useState<{ message: string; unavailable: boolean } | null>(null)
  const [busy, setBusy] = useState(false)

  const run = useCallback(
    async (action: AiAction) => {
      setActive(action)
      setBusy(true)
      setError(null)
      setData(null)
      try {
        setData(await action.run(question.trim()))
      } catch (err) {
        const failure = err as AiRequestError
        setError({
          message: failure.message,
          unavailable: failure instanceof AiRequestError && failure.isUnavailable,
        })
      } finally {
        setBusy(false)
      }
    },
    [question],
  )

  return (
    <section className={`ai-panel ${open ? 'is-open' : ''}`}>
      <button
        type="button"
        className="ai-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="ai-toggle-mark" aria-hidden="true">
          {open ? '−' : '+'}
        </span>
        {title}
        <span className="ai-toggle-hint">assistant · advisory only</span>
      </button>

      {open && (
        <div className="ai-body">
          <p className="muted">{lede}</p>

          {extras && <div className="ai-extras">{extras}</div>}

          <div className="ai-actions">
            {actions.map((action) => (
              <button
                key={action.key}
                type="button"
                className={active?.key === action.key ? 'active' : ''}
                title={action.hint}
                disabled={busy}
                onClick={() => run(action)}
              >
                {action.label}
              </button>
            ))}
          </div>

          {allowQuestion && (
            <label className="ai-question">
              <span className="muted">
                Optional — a question about this record, for the assistant to answer
                within the task above.
              </span>
              <input
                type="text"
                value={question}
                maxLength={500}
                placeholder="e.g. what would an auditor ask about the sampling here?"
                onChange={(event) => setQuestion(event.target.value)}
              />
            </label>
          )}

          {busy && (
            <p className="empty">
              Asking the local model… a first request after a cold start can take a
              while, and nothing else in the application is waiting on it.
            </p>
          )}

          {error && (
            <div
              className={`banner ${error.unavailable ? 'banner-warn' : 'banner-todo'}`}
              role="alert"
            >
              <strong>
                {error.unavailable
                  ? 'The assistant is not available.'
                  : 'The assistant could not answer.'}
              </strong>{' '}
              {error.message}
              {error.unavailable && ' Every other part of GRCShield is unaffected.'}
            </div>
          )}

          {data && active && <AiResult data={data}>{active.render(data)}</AiResult>}
        </div>
      )}
    </section>
  )
}

/** The wrapper every suggestion is shown inside. Label above, evidence of inputs
 *  below, provenance at the foot. */
function AiResult({ data, children }: { data: AiEnvelope; children: ReactNode }) {
  return (
    <article className="ai-result">
      <div className="ai-label">
        <span className="tag tag-todo">{data.label}</span>
        <p className="muted">{data.note}</p>
      </div>

      {data.guardrail_notes.length > 0 && (
        <div className="banner banner-warn" role="note">
          <strong>
            {data.guardrail_notes.length} output guardrail
            {data.guardrail_notes.length === 1 ? '' : 's'} fired on this suggestion.
          </strong>
          <ul>
            {data.guardrail_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="ai-content">{children}</div>

      <details className="ai-basis">
        <summary>What the model was given</summary>
        <ul>
          {data.context_provided.map((item) => (
            <li key={item.label}>
              <strong>{item.label}:</strong> {item.value}
            </li>
          ))}
        </ul>
        <p className="muted">
          Only these records were sent. The prompt is assembled on the server from named
          fields; the model has no access to the database, and none of its output has
          changed anything here.
        </p>
      </details>

      <p className="ai-foot muted">
        {data.provider} · {data.model} · {(data.latency_ms / 1000).toFixed(1)}s
        {data.interaction_ref && <> · logged as {data.interaction_ref}</>}
      </p>
    </article>
  )
}

/* --- Presentational helpers, so every suggestion body reads the same -------------- */

export function AiSection({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <div className="ai-section">
      <h4>{heading}</h4>
      {children}
    </div>
  )
}

export function AiList({ heading, items }: { heading: string; items: string[] }) {
  if (!items || items.length === 0) return null
  return (
    <AiSection heading={heading}>
      <ul className="ai-list">
        {items.map((item, index) => (
          <li key={`${heading}-${index}`}>{item}</li>
        ))}
      </ul>
    </AiSection>
  )
}

export function AiText({ heading, value }: { heading: string; value: string }) {
  if (!value || !value.trim()) return null
  return (
    <AiSection heading={heading}>
      <p>{value}</p>
    </AiSection>
  )
}

/** The anti-hallucination field, rendered deliberately rather than tucked away.
 *
 *  A model that says what it does not know is more useful than one that fills the gap,
 *  so this is given the same weight as the answer itself. When it is empty, saying so
 *  is also informative -- it tells the reader the model claimed nothing was missing,
 *  which is itself worth a second look. */
export function AiGaps({ items }: { items: string[] }) {
  return (
    <AiSection heading="What the assistant says it does not know">
      {items && items.length > 0 ? (
        <ul className="ai-list ai-list-gaps">
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">
          The assistant reported no missing information. That is a claim about its own
          answer, not a fact about the record.
        </p>
      )}
    </AiSection>
  )
}

export function AiConfidenceNote({ confidence }: { confidence: string }) {
  return (
    <p className="ai-confidence muted">
      Model-reported confidence: <strong>{confidence}</strong>. This is the model's
      account of its own output, not a measurement, and it carries no weight anywhere in
      the risk methodology.
    </p>
  )
}
