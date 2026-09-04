/* The consistency sweep — the assistant used as a reviewer rather than a writer.
 *
 * The page is a queue, not a chat box, and that is the whole design. Rules decide which
 * controls are worth asking about; the model does the reading, one control at a time,
 * only when somebody asks. So the page is useful with the model switched off — the queue
 * still tells an analyst where the tension in their ISMS is — and it gets better when the
 * model is on.
 */

import { useState } from 'react'

import {
  AiRequestError,
  aiApi,
  type AiConsistencySweep,
  type SweepCandidate,
} from '../ai'
import { useAsync } from '../useAsync'

interface SweepState {
  loading: boolean
  data: AiConsistencySweep | null
  error: { message: string; unavailable: boolean } | null
}

const IDLE: SweepState = { loading: false, data: null, error: null }

function Findings({ data }: { data: AiConsistencySweep }) {
  const { contradictions, consistent_aspects: consistent } = data.suggestion

  return (
    <div className="sweep-result">
      <div className="ai-label">
        <span className="tag tag-todo">{data.label}</span>
        <p className="muted">{data.note}</p>
      </div>

      {data.suggestion.summary && <p>{data.suggestion.summary}</p>}

      {contradictions.length === 0 ? (
        <p className="muted">
          The assistant reported no disagreement between these records. That is a claim
          about its reading, not a guarantee — it is one more opinion on the pile, and a
          clean sweep is worth roughly what a clean sweep by a junior reviewer is worth.
        </p>
      ) : (
        <ol className="sweep-list">
          {contradictions.map((item, index) => (
            <li key={index}>
              <div className="chain-row">
                {item.records.map((ref) => (
                  <code key={ref} className="chain-ref">
                    {ref}
                  </code>
                ))}
              </div>
              <p>
                <strong>{item.what_disagrees}</strong>
              </p>
              {item.why_it_matters && <p className="muted">{item.why_it_matters}</p>}
              {item.question_for_the_analyst && (
                <p className="sweep-question">{item.question_for_the_analyst}</p>
              )}
            </li>
          ))}
        </ol>
      )}

      {data.uncited_records.length > 0 && (
        <div className="banner banner-warn" role="note">
          <strong>
            {data.uncited_records.length} finding
            {data.uncited_records.length === 1 ? ' was' : 's were'} dropped for citing a
            record the model was never shown:
          </strong>{' '}
          {data.uncited_records.join(', ')}. An invented disagreement between two
          real-sounding record numbers reads exactly like a real one, so citations are
          checked against what was actually supplied.
        </div>
      )}

      {consistent.length > 0 && (
        <details className="ai-basis">
          <summary>Checked and found consistent ({consistent.length})</summary>
          <ul>
            {consistent.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </details>
      )}

      <details className="ai-basis">
        <summary>Records compared ({data.records_compared.length})</summary>
        <p className="muted">{data.records_compared.join(', ')}</p>
      </details>

      <p className="ai-foot muted">
        {data.provider} · {data.model} · {(data.latency_ms / 1000).toFixed(1)}s
        {data.interaction_ref && <> · logged as {data.interaction_ref}</>}
      </p>
    </div>
  )
}

function CandidateRow({ candidate }: { candidate: SweepCandidate }) {
  const [state, setState] = useState<SweepState>(IDLE)

  const sweep = async () => {
    setState({ loading: true, data: null, error: null })
    try {
      const data = await aiApi.consistencySweep(candidate.control_id)
      setState({ loading: false, data, error: null })
    } catch (err) {
      const failure = err as AiRequestError
      setState({
        loading: false,
        data: null,
        error: {
          message: failure.message,
          unavailable: failure instanceof AiRequestError && failure.isUnavailable,
        },
      })
    }
  }

  return (
    <article className="sweep-card">
      <div className="sweep-head">
        <div>
          <h3>
            <code>{candidate.control_id}</code> {candidate.title}
          </h3>
          <p className="card-meta">
            {candidate.record_count} records across {candidate.record_types.length} parts of
            the ISMS — {candidate.record_types.join(', ')}
          </p>
        </div>
        <button type="button" onClick={sweep} disabled={state.loading}>
          {state.loading ? 'Reading…' : 'Sweep'}
        </button>
      </div>

      <ul className="sweep-reasons">
        {candidate.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>

      {state.loading && (
        <p className="empty">
          Reading {candidate.record_count} records on this machine. Nothing else in the
          application is waiting on it.
        </p>
      )}

      {state.error && (
        <div
          className={`banner ${state.error.unavailable ? 'banner-warn' : 'banner-todo'}`}
          role="alert"
        >
          <strong>
            {state.error.unavailable
              ? 'The assistant is not available.'
              : 'The assistant could not answer.'}
          </strong>{' '}
          {state.error.message}
          {state.error.unavailable &&
            ' The queue above is computed without it and is unaffected.'}
        </div>
      )}

      {state.data && <Findings data={state.data} />}
    </article>
  )
}

export function Consistency() {
  const { data, error, loading } = useAsync(() => aiApi.consistencyCandidates(), [])

  return (
    <section>
      <h1>Consistency sweep</h1>
      <p className="lede">
        An ISMS goes wrong quietly. The same fact is recorded in several places, one of
        them is updated, and the others keep saying what used to be true. No validation
        rule catches that in general — the rule would have to be written once per pair of
        record types — but reading the records side by side does.
      </p>

      <div className="banner banner-todo" role="note">
        <strong>Rules pick the queue; the model does the reading.</strong> The list below
        is a plain database query: controls referenced from several parts of the system
        that also carry some tension — a failed test, an open finding, expired evidence,
        a risk claiming more assurance than the library supports. Those are the only
        places a contradiction can exist. The assistant is pointed at one at a time, and
        it reports disagreements rather than settling them.
      </div>

      {loading && <p className="empty">Working out where to look…</p>}
      {error && <p className="error">Could not load the queue: {error}</p>}

      {data && data.length === 0 && (
        <p className="empty">
          No control is referenced from enough places, with enough tension, to be worth
          sweeping. That is a good state and an unusual one.
        </p>
      )}

      {data && data.length > 0 && (
        <>
          <div className="tiles">
            <div className="tile tile-alert">
              <span className="tile-value">{data.length}</span>
              <span className="tile-label">controls worth checking</span>
            </div>
            <div className="tile">
              <span className="tile-value">
                {data.reduce((total, row) => total + row.record_count, 0)}
              </span>
              <span className="tile-label">records they touch</span>
            </div>
          </div>

          <div className="sweep-queue">
            {data.map((candidate) => (
              <CandidateRow key={candidate.control_id} candidate={candidate} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
