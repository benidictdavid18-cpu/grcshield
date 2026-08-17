import { api, openReport } from '../api'
import { useAsync } from '../useAsync'

const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export function Executive() {
  const { data, error, loading } = useAsync(() => api.executiveSummary(), [])

  if (loading) return <p className="empty">Loading…</p>
  if (error) return <p className="error">Could not load the summary: {error}</p>
  if (!data) return null

  return (
    <section className="executive">
      <div className="exec-head">
        <div>
          <h1>Executive summary</h1>
          <p className="card-meta">FinFlow Technologies · {data.as_of}</p>
        </div>
        <button
          type="button"
          className="primary"
          onClick={() => openReport(api.executiveReportUrl())}
        >
          Download PDF
        </button>
      </div>

      <p className="exec-lead">{data.posture_statement}</p>

      <div className="tiles">
        <div className="tile">
          <span className="tile-value">{data.safeguards_percent}%</span>
          <span className="tile-label">
            protections in place ({data.safeguards_in_place} of {data.safeguards_required})
          </span>
        </div>
        <div className={`tile ${data.risks_beyond_agreed_limit > 0 ? 'tile-alert' : ''}`}>
          <span className="tile-value">{data.risks_beyond_agreed_limit}</span>
          <span className="tile-label">
            exposures beyond agreed limits, of {data.risks_total} tracked
          </span>
        </div>
        <div className={`tile ${data.risks_carried_without_a_decision > 0 ? 'tile-alert' : ''}`}>
          <span className="tile-value">{data.risks_carried_without_a_decision}</span>
          <span className="tile-label">carried without anyone deciding to</span>
        </div>
        <div className={`tile ${data.remediation_overdue > 0 ? 'tile-todo' : ''}`}>
          <span className="tile-value">{data.remediation_overdue}</span>
          <span className="tile-label">
            pieces of work overdue, of {data.remediation_open} open
          </span>
        </div>
      </div>

      <h2>What we recommend doing next</h2>
      <ol className="priorities">
        {data.priorities.map((priority) => (
          <li key={priority.headline}>
            <h3>{priority.headline}</h3>
            <p>{priority.why}</p>
            <p className="muted">
              Owner: {priority.owner} · Target: {priority.by_when}
            </p>
          </li>
        ))}
      </ol>

      <h2>The five exposures that matter most</h2>
      <table className="register">
        <thead>
          <tr>
            <th>What could go wrong</th>
            <th>Assessment</th>
            <th>Owner</th>
          </tr>
        </thead>
        <tbody>
          {data.top_risks.map((risk) => (
            <tr key={risk.risk_ref}>
              <td>
                {risk.plain_title}
                {risk.beyond_agreed_limit && (
                  <span className="tag tag-breach">beyond agreed limit</span>
                )}
              </td>
              <td className="muted">{risk.what_could_happen}</td>
              <td>{risk.who_owns_it}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Where the biggest protection gaps are</h2>
      <table className="register">
        <thead>
          <tr>
            <th>Protection not yet fully in place</th>
            <th className="num">Exposures relying on it</th>
            <th>Owner</th>
          </tr>
        </thead>
        <tbody>
          {data.top_gaps.map((gap) => (
            <tr key={gap.what_is_missing}>
              <td>
                {gap.what_is_missing}
                {gap.detail && <span className="row-sub">{gap.detail}</span>}
              </td>
              <td className="num">{gap.risks_depending_on_it}</td>
              <td>{gap.owner}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="exec-columns">
        <div>
          <h2>Issues found by our own checks</h2>
          <p>
            {data.open_findings_total} issues are open from internal testing:{' '}
            {SEVERITY_ORDER.filter((s) => data.open_findings_by_severity[s] > 0)
              .map((s) => `${data.open_findings_by_severity[s]} ${s.toLowerCase()}`)
              .join(', ')}
            . Each has an owner and a date. Finding them ourselves is the system working;
            leaving them open past their date is not.
          </p>
        </div>
        <div>
          <h2>Suppliers</h2>
          <p>{data.third_party.summary}</p>
        </div>
      </div>
    </section>
  )
}
