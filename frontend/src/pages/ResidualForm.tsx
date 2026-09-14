import { useState } from 'react'

import { api, type RiskDetail } from '../api'
import { FieldError, UnplacedErrors, useSubmit } from '../editing'

const SCALE = [1, 2, 3, 4, 5]
const FIELDS = ['residual_likelihood', 'residual_impact', 'residual_justification']

/** Re-score residual risk.
 *
 *  Likelihood and impact are entered directly -- there is no effectiveness percentage
 *  to derive them from, on purpose. The two rules that can refuse the submission live
 *  on the server: a justification must say something, and a reduction below inherent
 *  must be attributable to a control that has actually been tested. When either fires,
 *  the API's own message appears under the field it names. */
export function ResidualForm({
  risk,
  onSaved,
}: {
  risk: RiskDetail
  onSaved: (r: RiskDetail) => void
}) {
  const [open, setOpen] = useState(false)
  const [likelihood, setLikelihood] = useState(risk.residual.likelihood)
  const [impact, setImpact] = useState(risk.residual.impact)
  const [justification, setJustification] = useState(risk.residual_justification)

  const { state, submit, reset } = useSubmit(
    () =>
      api.updateResidual(risk.risk_ref, {
        residual_likelihood: likelihood,
        residual_impact: impact,
        residual_justification: justification,
      }),
    (updated) => {
      onSaved(updated)
      setOpen(false)
    },
  )

  const proposed = likelihood * impact
  const belowInherent = proposed < risk.inherent.score
  const anyCredited = risk.controls.some((c) => c.credits_reduction)

  return (
    <section className={`edit-panel ${open ? 'is-open' : ''}`}>
      <button
        type="button"
        className="ai-toggle"
        onClick={() => {
          setOpen(!open)
          reset()
        }}
        aria-expanded={open}
      >
        <span className="ai-toggle-mark" aria-hidden="true">
          {open ? '−' : '+'}
        </span>
        Re-score residual risk
        <span className="ai-toggle-hint">writes to the register · rule-checked</span>
      </button>

      {open && (
        <form className="edit-form" onSubmit={submit} noValidate>
          <p className="muted">
            Inherent is {risk.inherent.likelihood} × {risk.inherent.impact} = {risk.inherent.score}.
            Residual is scored independently; impact usually does not move.
            {belowInherent && !anyCredited && (
              <>
                {' '}
                <strong>
                  No linked control is credited, so the API will refuse a score below inherent.
                </strong>{' '}
                Submit anyway to see the refusal.
              </>
            )}
          </p>

          <div className="edit-fields">
            <label>
              Residual likelihood
              <select
                name="residual_likelihood"
                value={likelihood}
                onChange={(e) => setLikelihood(Number(e.target.value))}
              >
                {SCALE.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              <FieldError refusal={state.refusal} field="residual_likelihood" />
            </label>
            <label>
              Residual impact
              <select
                name="residual_impact"
                value={impact}
                onChange={(e) => setImpact(Number(e.target.value))}
              >
                {SCALE.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              <FieldError refusal={state.refusal} field="residual_impact" />
            </label>
            <div className="edit-preview">
              Proposed: <strong>{proposed}</strong>
            </div>
          </div>

          <label className="edit-wide">
            Residual justification
            <textarea
              name="residual_justification"
              rows={4}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Which control moved which dimension, and on what evidence."
            />
            <FieldError refusal={state.refusal} field="residual_justification" />
          </label>

          <UnplacedErrors refusal={state.refusal} shown={FIELDS} />
          {state.message && (
            <div className="banner banner-warn" role="alert">
              {state.message}
            </div>
          )}

          <div className="edit-actions">
            <button type="submit" className="primary" disabled={state.busy}>
              {state.busy ? 'Saving…' : 'Save residual score'}
            </button>
            <button type="button" onClick={() => setOpen(false)} disabled={state.busy}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
