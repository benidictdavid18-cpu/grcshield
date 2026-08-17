import { api, openReport } from '../api'
import { useAsync } from '../useAsync'

export function Reports() {
  const { data, error, loading } = useAsync(() => api.reports(), [])

  if (loading) return <p className="empty">Loading reports…</p>
  if (error) return <p className="error">Could not load reports: {error}</p>
  if (!data) return null

  return (
    <section>
      <h1>Reports</h1>
      <p className="lede">
        Three reports, each with a named audience and a decision it supports. A report nobody would
        act on is a chart with a cover page.
      </p>

      <div className="cards">
        {data.map((report) => (
          <article key={report.code} className="card">
            <div className="card-head">
              <span className={`badge ${report.implemented ? 'badge-primary' : 'badge-roadmap'}`}>
                {report.implemented ? 'Available' : `Phase ${report.available_from_phase}`}
              </span>
            </div>
            <h2>{report.title}</h2>
            <p className="card-meta">For: {report.audience}</p>
            <p className="card-note">{report.decision_supported}</p>
            {report.endpoint && (
              <button
                type="button"
                className="card-link"
                onClick={() => openReport(`/api${report.endpoint}`)}
              >
                Open PDF →
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
