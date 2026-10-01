import { type RiskDetail } from './api'
import { Reference } from './RecordDrawer'
import { BASIS_LABEL } from './risk-labels'

export function RiskGraph({ risk }: { risk: RiskDetail }) {
  return (
    <section className="risk-graph" aria-label="Interactive risk evidence graph">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Trace the assessment</span>
          <h2>From exposure to evidence</h2>
        </div>
        <span className="muted">Select a node to inspect its record</span>
      </div>
      <div className="graph-layout">
        <div className="graph-node graph-origin">
          <span className="eyebrow">Inherent exposure</span>
          <Reference value={risk.risk_ref} />
          <strong>
            {risk.inherent.score} <small>{risk.inherent.band.toLowerCase()}</small>
          </strong>
          <p>{risk.title}</p>
        </div>
        <div className="graph-branches">
          {risk.controls.map((control) => (
            <div className="graph-branch" key={control.control_id}>
              <div
                className="graph-edge"
                tabIndex={0}
                aria-label={`Basis: ${BASIS_LABEL[control.effectiveness_basis]}. ${control.note ?? ''}`}
              >
                <span>{BASIS_LABEL[control.effectiveness_basis]}</span>
                <div className="edge-detail">{control.note ?? 'No additional basis recorded.'}</div>
              </div>
              <div className={`graph-node ${control.credits_reduction ? '' : 'graph-uncredited'}`}>
                <Reference value={control.control_id} />
                <p>{control.title}</p>
                <span className={`tag ${control.credits_reduction ? 'tag-ok' : 'tag-warn'}`}>
                  {control.credits_reduction ? 'Credited basis' : 'No reduction credit'}
                </span>
                <div>
                  {control.annex_a_refs.map((ref) => (
                    <Reference key={ref} value={ref} />
                  ))}
                </div>
              </div>
              <div
                className="graph-edge"
                tabIndex={0}
                aria-label={`Workpaper basis: ${control.proof_state ?? 'not recorded'}`}
              >
                <span>
                  {control.proof_state?.replace(/_/g, ' ').toLowerCase() ?? 'proof not recorded'}
                </span>
                <div className="edge-detail">
                  {control.proof_note ??
                    'A linked test alone does not establish effective operation.'}
                </div>
              </div>
              <div className="graph-node graph-test">
                {control.supporting_test_ref ? (
                  <>
                    <span className="eyebrow">Supporting workpaper</span>
                    <Reference value={control.supporting_test_ref} />
                    <p>
                      {control.test_period_start} – {control.test_period_end}
                    </p>
                  </>
                ) : (
                  <>
                    <span className="tag tag-warn">No supporting workpaper</span>
                    <p>No test evidence linked to this assessment.</p>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="graph-node graph-result">
          <span className="eyebrow">Assessed residual</span>
          <strong>
            {risk.residual.score} <small>{risk.residual.band.toLowerCase()}</small>
          </strong>
          <p>Independently scored by the analyst.</p>
          <span className={`tag ${risk.appetite.exceeds_appetite ? 'tag-breach' : 'tag-ok'}`}>
            {risk.appetite.exceeds_appetite === null
              ? 'Appetite not set'
              : risk.appetite.exceeds_appetite
                ? 'Above appetite'
                : 'Within appetite'}
          </span>
        </div>
      </div>
    </section>
  )
}
