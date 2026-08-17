import { api } from '../api'
import { useAsync } from '../useAsync'

export function Roadmap() {
  const { data, error, loading } = useAsync(() => api.frameworks(), [])

  if (loading) return <p className="empty">Loading…</p>
  if (error) return <p className="error">Could not load frameworks: {error}</p>

  const roadmap = (data ?? []).filter((framework) => framework.scope_status === 'ROADMAP')

  return (
    <section>
      <h1>Roadmap — not yet assessed</h1>
      <p className="lede">
        These frameworks are registered but carry no assessment data. They are shown here rather
        than hidden, and deliberately have no progress bars: a percentage against controls nobody
        has evaluated is a number that reads as assurance and carries none.
      </p>

      {roadmap.map((framework) => (
        <article key={framework.code} className="roadmap-item">
          <h2>{framework.name}</h2>
          <p className="card-meta">
            {framework.publisher} · {framework.version}
          </p>
          <p>{framework.scope_note}</p>
        </article>
      ))}

      <div className="roadmap-note">
        <h3>What is still in scope from GDPR</h3>
        <p>
          Descoping GDPR as a scored framework does not remove the obligation. Two operational
          artefacts are built as first-class modules: the Record of Processing Activities
          (Article&nbsp;30) and Data Protection Impact Assessments (Article&nbsp;35). Legal and
          regulatory obligations enter the ISMS through A.5.31, and PII protection through A.5.34.
        </p>
      </div>
    </section>
  )
}
