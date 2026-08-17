import { Link, useParams } from 'react-router-dom'

import { api, type Score } from '../api'
import { useAsync } from '../useAsync'
import {
  BASIS_LABEL,
  BASIS_MEANING,
  STATUS_LABEL,
  TODO_MARKER,
  TREATMENT_LABEL,
} from '../risk-labels'

function ScoreBlock({ label, score, note }: { label: string; score: Score; note: string }) {
  return (
    <div className={`score-block band-edge-${score.band.toLowerCase()}`}>
      <h3>{label}</h3>
      <p className="score-maths">
        <span title="Likelihood">L {score.likelihood}</span>
        <span className="times">×</span>
        <span title="Impact">I {score.impact}</span>
        <span className="equals">=</span>
        <strong>{score.score}</strong>
        <span className={`band band-${score.band.toLowerCase()}`}>{score.band.toLowerCase()}</span>
      </p>
      <p className="muted">{note}</p>
    </div>
  )
}

export function RiskDetail() {
  const { riskRef = '' } = useParams()
  const { data: risk, error, loading } = useAsync(() => api.risk(riskRef), [riskRef])

  if (loading) return <p className="empty">Loading risk…</p>
  if (error) return <p className="error">Could not load {riskRef}: {error}</p>
  if (!risk) return null

  const uncredited = risk.controls.filter((control) => !control.credits_reduction)
  const justificationOutstanding = risk.residual_justification.includes(TODO_MARKER)
  const dimensionsMoved = [
    risk.inherent.likelihood !== risk.residual.likelihood ? 'likelihood' : null,
    risk.inherent.impact !== risk.residual.impact ? 'impact' : null,
  ].filter(Boolean)

  return (
    <section className="risk-detail">
      <p className="crumb">
        <Link to="/risks">← Risk register</Link>
      </p>

      <h1>
        <span className="risk-ref">{risk.risk_ref}</span> {risk.title}
      </h1>
      <p className="card-meta">
        {risk.category_label} · owned by {risk.owner_role} · {STATUS_LABEL[risk.status]} ·
        identified {risk.date_identified} · next review {risk.next_review ?? 'not set'}
      </p>
      <p>{risk.description}</p>

      {uncredited.length > 0 && (
        <div className="banner banner-warn" role="alert">
          <strong>
            {uncredited.length} linked control{uncredited.length > 1 ? 's' : ''} may not be
            credited with any residual reduction.
          </strong>{' '}
          {uncredited.map((control) => control.control_id).join(', ')} —{' '}
          {uncredited.every((control) => control.effectiveness_basis === 'NOT_TESTED')
            ? 'never tested, so the control is an intention rather than evidence.'
            : 'untested or tested ineffective.'}{' '}
          {uncredited.length === risk.controls.length
            ? 'No control on this risk may be credited, so residual cannot be scored below inherent.'
            : 'Any reduction claimed below must be attributable to the remaining controls.'}
        </div>
      )}

      {justificationOutstanding && (
        <div className="banner banner-todo" role="note">
          <strong>Residual justification not yet written.</strong> This field is reserved for
          the author and is not machine-generated.
        </div>
      )}

      {/* The calculation, rendered as a chain rather than a result. */}
      <div className="chain">
        <ScoreBlock
          label="1. Inherent risk"
          score={risk.inherent}
          note="Before any control is considered."
        />

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <div className="score-block">
          <h3>2. Controls applied</h3>
          <ul className="control-list">
            {risk.controls.map((control) => (
              <li key={control.control_id} className={control.credits_reduction ? '' : 'uncredited'}>
                <div className="control-head">
                  <code>{control.control_id}</code>
                  <span className={`basis basis-${control.effectiveness_basis.toLowerCase()}`}>
                    {BASIS_LABEL[control.effectiveness_basis]}
                  </span>
                  {!control.credits_reduction && <span className="tag tag-warn">no credit</span>}
                </div>
                <p>{control.title}</p>
                <p className="muted">{BASIS_MEANING[control.effectiveness_basis]}</p>
                <p className="muted">
                  Annex A: {control.annex_a_refs.join(', ')} · owned by {control.owner_role}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <ScoreBlock
          label="3. Residual risk"
          score={risk.residual}
          note={
            dimensionsMoved.length === 0
              ? 'No reduction claimed — residual equals inherent.'
              : dimensionsMoved.length === 2
                ? 'Scored directly by the analyst. Both likelihood and impact moved.'
                : `Scored directly by the analyst. ${dimensionsMoved[0] === 'likelihood' ? 'Likelihood' : 'Impact'} moved; ${dimensionsMoved[0] === 'likelihood' ? 'impact' : 'likelihood'} did not.`
          }
        />

        <div className="justification">
          <h4>Residual justification</h4>
          <p className={justificationOutstanding ? 'todo-text' : ''}>
            {risk.residual_justification}
          </p>
        </div>

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <div
          className={`score-block appetite-block ${
            risk.appetite.exceeds_appetite ? 'is-breach' : 'is-within'
          }`}
        >
          <h3>4. Appetite comparison</h3>
          {risk.appetite.max_acceptable_band === null ? (
            <p>
              No appetite is defined for {risk.category_label}. This is an unanswered governance
              question, not an implicit acceptance.
            </p>
          ) : (
            <p className="score-maths">
              residual{' '}
              <span className={`band band-${risk.residual.band.toLowerCase()}`}>
                {risk.residual.band.toLowerCase()}
              </span>
              <span className="equals">vs</span>
              ceiling{' '}
              <span className={`band band-${risk.appetite.max_acceptable_band.toLowerCase()}`}>
                {risk.appetite.max_acceptable_band.toLowerCase()}
              </span>
              <span className={`tag ${risk.appetite.exceeds_appetite ? 'tag-breach' : 'tag-ok'}`}>
                {risk.appetite.exceeds_appetite ? 'above appetite' : 'within appetite'}
              </span>
            </p>
          )}
          {risk.appetite.approver_role && (
            <p className="muted">
              Appetite for {risk.category_label} is set and accepted by the{' '}
              {risk.appetite.approver_role}. Risk acceptance is a business decision, not a
              security decision.
            </p>
          )}
        </div>

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <div className="score-block">
          <h3>5. Treatment decision</h3>
          <p className="treatment-decision">{TREATMENT_LABEL[risk.treatment_decision]}</p>
          <p>{risk.treatment_summary}</p>
        </div>
      </div>

      <div className="analysis-grid">
        <div>
          <h4>Asset</h4>
          <p>{risk.asset}</p>
        </div>
        <div>
          <h4>Threat</h4>
          <p>{risk.threat}</p>
        </div>
        <div>
          <h4>Vulnerability</h4>
          <p>{risk.vulnerability}</p>
        </div>
      </div>
    </section>
  )
}
