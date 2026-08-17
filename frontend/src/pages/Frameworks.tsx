import { Link } from 'react-router-dom'

import { api, type ScopeStatus } from '../api'
import { useAsync } from '../useAsync'

const SCOPE_LABEL: Record<ScopeStatus, string> = {
  PRIMARY: 'Primary — assessed',
  SECONDARY: 'Secondary — mapped',
  ROADMAP: 'Roadmap — not yet assessed',
}

export function Frameworks() {
  const { data, error, loading } = useAsync(() => api.frameworks(), [])

  if (loading) return <p className="empty">Loading frameworks…</p>
  if (error) return <p className="error">Could not load frameworks: {error}</p>
  if (!data) return null

  return (
    <section>
      <h1>Frameworks</h1>
      <p className="lede">
        Depth over breadth. One framework is assessed in full; one is reached by mapping from it;
        the rest are catalogued honestly as not yet assessed.
      </p>

      <div className="cards">
        {data.map((framework) => (
          <article key={framework.code} className={`card scope-${framework.scope_status.toLowerCase()}`}>
            <div className="card-head">
              <span className={`badge badge-${framework.scope_status.toLowerCase()}`}>
                {SCOPE_LABEL[framework.scope_status]}
              </span>
              <span className="card-count">
                {framework.control_count > 0 ? `${framework.control_count} controls` : 'no catalogue'}
              </span>
            </div>
            <h2>{framework.name}</h2>
            <p className="card-meta">
              {framework.publisher} · {framework.version}
            </p>
            <p className="card-note">{framework.scope_note}</p>
            {framework.control_count > 0 && (
              <Link className="card-link" to={`/controls?framework=${framework.code}`}>
                Browse controls →
              </Link>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
