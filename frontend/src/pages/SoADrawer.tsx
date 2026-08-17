import { Link } from 'react-router-dom'

import { api } from '../api'
import { useAsync } from '../useAsync'
import {
  CONCLUSION_LABEL,
  IMPLEMENTATION_LABEL,
  REMEDIATION_LABEL,
  TREATMENT_LABEL,
} from '../risk-labels'

/** One link in the traceability chain. */
function ChainStep({
  index,
  label,
  count,
  empty,
  children,
}: {
  index: number
  label: string
  count?: number
  empty?: string
  children?: React.ReactNode
}) {
  return (
    <div className="chain-step">
      <div className="chain-step-head">
        <span className="chain-step-index">{index}</span>
        <h4>{label}</h4>
        {count !== undefined && <span className="chain-step-count">{count}</span>}
      </div>
      <div className="chain-step-body">
        {/* Callers pass `cond && <jsx/>`, which yields `false` rather than undefined
            when the condition fails -- so test truthiness, not nullishness. */}
        {children ? children : <p className="muted">{empty}</p>}
      </div>
    </div>
  )
}

export function SoADrawer({ controlRef, onClose }: { controlRef: string; onClose: () => void }) {
  const { data, error, loading } = useAsync(() => api.soaEntry(controlRef), [controlRef])

  return (
    <aside className="drawer soa-drawer">
      <div className="drawer-head">
        <h2>{controlRef}</h2>
        <button type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      {loading && <p className="empty">Loading…</p>}
      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <p className="drawer-title">{data.control_title}</p>
          <p className="card-meta">
            {data.theme} · owned by {data.owner} · v{data.version}, approved by{' '}
            {data.approved_by ?? 'nobody'} on {data.approved_date ?? '—'}
          </p>

          <div className={`scope-block ${data.applicable ? 'is-in' : 'is-out'}`}>
            <strong>
              {data.applicable ? 'Applicable' : 'Excluded'} ·{' '}
              {IMPLEMENTATION_LABEL[data.implementation_status]}
            </strong>
            <p>
              {data.applicable ? data.justification_inclusion : data.justification_exclusion}
            </p>
            {data.justification_outstanding && (
              <p className="todo-text">
                Justification reserved for the author — not machine-generated.
              </p>
            )}
          </div>

          {data.validation_errors.length > 0 && (
            <div className="banner banner-warn" role="alert">
              <strong>This entry currently fails validation.</strong>
              <ul>
                {data.validation_errors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}

          <h3>Traceability chain</h3>
          <div className="chain-steps">
            <ChainStep
              index={1}
              label="Risk"
              count={data.risks.length}
              empty={
                data.applicable
                  ? 'No risk drives this control — the inclusion justification must then rest on a legal, regulatory or contractual obligation.'
                  : 'Not applicable, so no risk is treated by this control.'
              }
            >
              {data.risks.length > 0 && (
                <ul className="chain-list">
                  {data.risks.map((risk) => (
                    <li key={risk.risk_ref}>
                      <div className="chain-row">
                        <Link to={`/risks/${risk.risk_ref}`} className="chain-ref">
                          {risk.risk_ref}
                        </Link>
                        <span className={`band band-${risk.residual_band.toLowerCase()}`}>
                          {risk.residual_score}
                        </span>
                        {risk.exceeds_appetite && (
                          <span className="tag tag-breach">above appetite</span>
                        )}
                      </div>
                      <p>{risk.title}</p>
                      <p className="muted">
                        Treatment: {TREATMENT_LABEL[risk.treatment_decision]} · {risk.category_label}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </ChainStep>

            <ChainStep
              index={2}
              label="Internal control"
              count={data.controls.length}
              empty={
                data.applicable
                  ? 'No internal control implements this yet — consistent with a not-implemented status.'
                  : 'Nothing is operated for an excluded control.'
              }
            >
              {data.controls.length > 0 && (
                <ul className="chain-list">
                  {data.controls.map((control) => (
                    <li key={control.control_id}>
                      <div className="chain-row">
                        <code className="chain-ref">{control.control_id}</code>
                        <span className="muted">{control.control_family}</span>
                      </div>
                      <p>{control.title}</p>
                      <p className="muted">Owned by {control.owner_role}</p>
                    </li>
                  ))}
                </ul>
              )}
            </ChainStep>

            <ChainStep
              index={3}
              label="Evidence"
              count={data.evidence.length}
              empty={
                data.implementation_status === 'IMPLEMENTED'
                  ? 'No evidence is linked. An implemented control with no evidence is an assertion, not a control.'
                  : 'No evidence yet.'
              }
            >
              {data.evidence.length > 0 && (
                <ul className="chain-list">
                  {data.evidence.map((item) => (
                    <li key={item.evidence_ref} className={item.expired ? 'uncredited' : ''}>
                      <div className="chain-row">
                        <code className="chain-ref">{item.evidence_ref}</code>
                        <span className="basis basis-design_only">{item.evidence_type}</span>
                        {item.expired && <span className="tag tag-warn">expired</span>}
                      </div>
                      <p>{item.title}</p>
                      <p className="muted">
                        {item.source_system} · valid {item.valid_from} to {item.valid_until}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </ChainStep>

            <ChainStep
              index={4}
              label="Test result"
              count={data.tests.length}
              empty="No control test covers this yet. The controls behind it are rated from review rather than sample testing."
            >
              {data.tests.length > 0 && (
                <ul className="chain-list">
                  {data.tests.map((test) => (
                    <li key={test.test_ref}>
                      <div className="chain-row">
                        <code className="chain-ref">{test.test_ref}</code>
                        <span className={`concl concl-${test.conclusion.toLowerCase()}`}>
                          {CONCLUSION_LABEL[test.conclusion]}
                        </span>
                        {test.finding_ref && (
                          <span className="tag tag-warn">{test.finding_ref}</span>
                        )}
                      </div>
                      <p>
                        <code>{test.control_id}</code> · {test.exceptions_count} exception
                        {test.exceptions_count === 1 ? '' : 's'} in a sample of{' '}
                        {test.sample_size} of {test.population_size}
                      </p>
                      <p className="muted">Tested {test.test_date}</p>
                    </li>
                  ))}
                </ul>
              )}
            </ChainStep>

            <ChainStep
              index={5}
              label="Gap"
              empty={
                data.applicable
                  ? 'No gap — this control is implemented.'
                  : 'No gap — this control is excluded from scope.'
              }
            >
              {data.is_gap && (
                <p>
                  Applicable and {IMPLEMENTATION_LABEL[data.implementation_status].toLowerCase()}.
                  {data.implementation_description
                    ? ` ${data.implementation_description}`
                    : ''}
                </p>
              )}
            </ChainStep>

            <ChainStep
              index={6}
              label="Remediation"
              count={data.remediation.length}
              empty={
                data.is_gap
                  ? 'No remediation linked — this entry fails validation.'
                  : 'No remediation needed.'
              }
            >
              {data.remediation.length > 0 && (
                <ul className="chain-list">
                  {data.remediation.map((item) => (
                    <li
                      key={item.remediation_ref}
                      className={item.status === 'COMPLETED' ? 'uncredited' : ''}
                    >
                      <div className="chain-row">
                        <code className="chain-ref">{item.remediation_ref}</code>
                        <span className="muted">{REMEDIATION_LABEL[item.status]}</span>
                        {item.overdue && <span className="tag tag-breach">overdue</span>}
                      </div>
                      <p>{item.title}</p>
                      <p className="muted">
                        {item.owner} · due {item.due_date}
                        {item.completed_date && ` · closed ${item.completed_date}`}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </ChainStep>

            <ChainStep
              index={7}
              label="Residual risk"
              empty="No linked risk to carry a residual score."
            >
              {data.risks.length > 0 && (
                <ul className="chain-list">
                  {data.risks.map((risk) => (
                    <li key={risk.risk_ref}>
                      <div className="chain-row">
                        <span className="chain-ref">{risk.risk_ref}</span>
                        <span className={`band band-${risk.residual_band.toLowerCase()}`}>
                          {risk.residual_score} {risk.residual_band.toLowerCase()}
                        </span>
                        <span className={`tag ${risk.exceeds_appetite ? 'tag-breach' : 'tag-ok'}`}>
                          {risk.exceeds_appetite ? 'above appetite' : 'within appetite'}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </ChainStep>
          </div>

          {data.implementation_description && (
            <>
              <h3>Implementation</h3>
              <p className="muted">{data.implementation_description}</p>
            </>
          )}

          <h3>Review</h3>
          <p className="muted">
            Last reviewed {data.last_reviewed ?? '—'} · next review {data.next_review ?? '—'}
          </p>
        </>
      )}
    </aside>
  )
}
