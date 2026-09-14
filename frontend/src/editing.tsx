import { useState } from 'react'

import { api, ApiValidationError } from './api'
import { useAsync } from './useAsync'

/* --- Forms that let the API say no --------------------------------------------
 *
 * The rules live on the server. A form here does not duplicate them; it submits, and
 * when the API refuses with `422` and a field name, it puts the message next to that
 * field. Client-side checks are limited to what HTML can express (required, a number
 * in range). The point of the product is that the refusal is real, so the form shows
 * the real one.
 */

export interface SubmitState {
  busy: boolean
  /** Whole-form message: a plain-sentence refusal, a 403, a network failure. */
  message: string | null
  /** Set when the refusal named fields. */
  refusal: ApiValidationError | null
  saved: boolean
}

const IDLE: SubmitState = { busy: false, message: null, refusal: null, saved: false }

/** Runs a write and turns its outcome into something a form can render. */
export function useSubmit<T>(write: () => Promise<T>, onSaved: (result: T) => void) {
  const [state, setState] = useState<SubmitState>(IDLE)

  async function submit(event?: React.FormEvent) {
    event?.preventDefault()
    setState({ ...IDLE, busy: true })
    try {
      const result = await write()
      setState({ ...IDLE, saved: true })
      onSaved(result)
    } catch (err) {
      if (err instanceof ApiValidationError) {
        setState({
          busy: false,
          saved: false,
          refusal: err,
          // A refusal with field errors is explained field by field; the top-level
          // message would only repeat it. A refusal without them is one sentence,
          // and that sentence is the explanation.
          message: err.fieldErrors.length ? null : err.message,
        })
      } else {
        setState({ ...IDLE, message: (err as Error).message })
      }
    }
  }

  return { state, submit, reset: () => setState(IDLE) }
}

/** The message for one field, rendered under it, if the API named that field. */
export function FieldError({
  refusal,
  field,
}: {
  refusal: ApiValidationError | null
  field: string
}) {
  const message = refusal?.for(field)
  if (!message) return null
  return (
    <p className="field-error" role="alert">
      {message}
    </p>
  )
}

/** Errors the API returned for fields this form does not show. Without this, an
 *  entry that fails on a field the form omits would be refused with no visible reason. */
export function UnplacedErrors({
  refusal,
  shown,
}: {
  refusal: ApiValidationError | null
  shown: string[]
}) {
  const rest = refusal?.fieldErrors.filter((e) => !shown.includes(e.field)) ?? []
  if (rest.length === 0) return null
  return (
    <div className="banner banner-warn" role="alert">
      <strong>Refused by a rule on a field this form does not edit.</strong>
      <ul>
        {rest.map((e) => (
          <li key={`${e.field}:${e.message}`}>
            <code>{e.field}</code> — {e.message}
          </li>
        ))}
      </ul>
    </div>
  )
}

/* --- Change history ------------------------------------------------------------
 *
 * The application's audit trail for one record. Readable by every role: the auditor
 * account exists precisely to ask "who changed this, and from what?".
 */

const ACTION_LABEL: Record<string, string> = {
  RESIDUAL_RESCORED: 'Residual re-scored',
  SOA_ENTRY_UPDATED: 'SoA entry updated',
  CONTROL_EFFECTIVENESS_UPDATED: 'Effectiveness re-rated',
  CONTROL_TEST_RECORDED: 'Workpaper recorded',
  RISK_EXCEPTION_RECORDED: 'Acceptance recorded',
}

function formatWhen(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function ChangeHistory({ recordRef, version }: { recordRef: string; version: number }) {
  const { data, error, loading } = useAsync(
    () => api.auditEvents({ record_ref: recordRef, limit: '20' }),
    [recordRef, version],
  )
  const [open, setOpen] = useState<number | null>(null)

  return (
    <section className="history">
      <h3>Change history</h3>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {data && data.length === 0 && (
        <p className="muted">
          No changes recorded through the application. What is shown is the seeded assessment as
          loaded.
        </p>
      )}
      {data && data.length > 0 && (
        <ol className="history-list">
          {data.map((event) => (
            <li key={event.id}>
              <div className="history-head">
                <span className="history-action">{ACTION_LABEL[event.action] ?? event.action}</span>
                <span className="muted">
                  {event.actor_username} · {formatWhen(event.occurred_at)}
                </span>
              </div>
              <p>{event.summary}</p>
              <button
                type="button"
                className="history-toggle"
                onClick={() => setOpen(open === event.id ? null : event.id)}
                aria-expanded={open === event.id}
              >
                {open === event.id ? 'Hide values' : 'Before and after'}
              </button>
              {open === event.id && (
                <table className="history-diff">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Before</th>
                      <th>After</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(event.after).map((field) => {
                      const before = event.before?.[field]
                      const after = event.after[field]
                      const changed = JSON.stringify(before) !== JSON.stringify(after)
                      return (
                        <tr key={field} className={changed ? 'is-changed' : ''}>
                          <td>
                            <code>{field}</code>
                          </td>
                          <td>{event.before ? String(before ?? '—') : '—'}</td>
                          <td>{String(after ?? '—')}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
