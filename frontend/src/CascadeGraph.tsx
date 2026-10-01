import { api } from './api'
import { Reference } from './RecordDrawer'
import { useAsync } from './useAsync'

interface Trace {
  control_ref: string
  design_effectiveness: string
  operating_effectiveness: string
  risks: {
    risk_ref: string
    title: string
    basis: string
    note: string | null
    credits_reduction: boolean
  }[]
  tests: { test_ref: string; conclusion: string; finding_ref: string | null }[]
  findings: {
    finding_ref: string
    title: string
    status: string
    remediation: { remediation_ref: string; title: string; status: string }[]
  }[]
}
export function CascadeGraph({ controlRef }: { controlRef: string }) {
  const { data, error, loading } = useAsync(
    () => api.read<Trace>(`/internal-controls/${encodeURIComponent(controlRef)}/trace`),
    [controlRef],
  )
  if (loading)
    return (
      <div className="skeleton" role="status">
        Tracing linked workpapers and risks…
      </div>
    )
  if (error) return <p className="error">Could not load the cascade: {error}</p>
  if (!data) return null
  return (
    <section className="risk-graph cascade">
      <h3>Test → finding → action → risk review</h3>
      <p className="muted">
        Relationships retained in the register. A test result never automatically re-scores a risk.
      </p>
      <div className="graph-node">
        <Reference value={controlRef} />
        <p>
          Design: {data.design_effectiveness.toLowerCase()} · Operating:{' '}
          {data.operating_effectiveness.toLowerCase().replace(/_/g, ' ')}
        </p>
      </div>
      {data.tests.map((test) => {
        const finding = data.findings.find((item) => item.finding_ref === test.finding_ref)
        return (
          <div className="cascade-row" key={test.test_ref}>
            <div className="graph-node">
              <Reference value={test.test_ref} />
              <p>{test.conclusion.replace(/_/g, ' ').toLowerCase()}</p>
            </div>
            <div className="graph-edge" tabIndex={0} aria-label="Test's explicitly linked finding">
              <span>recorded finding →</span>
            </div>
            <div className="graph-node">
              {finding ? (
                <>
                  <Reference value={finding.finding_ref} />
                  <p>{finding.title}</p>
                  <span className="tag">{finding.status.toLowerCase()}</span>
                </>
              ) : (
                <p>No finding linked to this test.</p>
              )}
            </div>
            {finding && (
              <>
                <div
                  className="graph-edge"
                  tabIndex={0}
                  aria-label="Actions explicitly linked to the finding"
                >
                  <span>owned actions →</span>
                </div>
                <div className="graph-node">
                  {finding.remediation.length ? (
                    finding.remediation.map((item) => (
                      <p key={item.remediation_ref}>
                        <Reference value={item.remediation_ref} /> · {item.status.toLowerCase()}
                      </p>
                    ))
                  ) : (
                    <p>No action linked.</p>
                  )}
                </div>
              </>
            )}
          </div>
        )
      })}
      <h4>Risks linked to this control</h4>
      <div className="cascade-risks">
        {data.risks.map((risk) => (
          <div className="graph-node" key={risk.risk_ref}>
            <Reference value={risk.risk_ref} />
            <p>{risk.title}</p>
            <span className={`tag ${risk.credits_reduction ? 'tag-ok' : 'tag-warn'}`}>
              {risk.credits_reduction ? 'Credited basis' : 'No reduction credit'}
            </span>
            <details>
              <summary>Read edge basis</summary>
              <p>
                {risk.basis.replace(/_/g, ' ').toLowerCase()}:{' '}
                {risk.note ?? 'No additional note recorded.'}
              </p>
            </details>
          </div>
        ))}
      </div>
    </section>
  )
}
