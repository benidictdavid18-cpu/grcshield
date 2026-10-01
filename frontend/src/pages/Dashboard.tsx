import { SecurityScene } from '../SecurityScene'
import { Link } from 'react-router-dom'
import { KriTrend, RiskHeatmap } from '../Charts'
import { useState } from 'react'

import { api, type Kri } from '../api'
import { useAsync } from '../useAsync'

const UNIT_SUFFIX: Record<string, string> = { PERCENT: '%', DAYS: 'd', COUNT: '' }

const MOVEMENT_LABEL: Record<string, string> = {
  IMPROVING: 'improving',
  DETERIORATING: 'getting worse',
  FLAT: 'unchanged',
  NO_TREND: 'no trend yet',
}

function KriCard({ kri }: { kri: Kri }) {
  const [open, setOpen] = useState(false)
  const suffix = UNIT_SUFFIX[kri.unit]
  const target =
    kri.direction === 'HIGHER_IS_BETTER'
      ? `≥ ${kri.green_threshold}${suffix}`
      : `≤ ${kri.green_threshold}${suffix}`

  return (
    <article className={`kri-card kri-${kri.current_band.toLowerCase()}`}>
      <div className="kri-head">
        <code className="chip">{kri.kri_ref}</code>
        <span className={`kri-band kri-band-${kri.current_band.toLowerCase()}`}>
          {kri.current_band === 'NO_DATA' ? 'not measured' : kri.current_band.toLowerCase()}
        </span>
      </div>
      <h3>{kri.name}</h3>
      <p className="kri-value">
        {kri.current_value === null ? '—' : `${kri.current_value}${suffix}`}
        <span className="kri-target">target {target}</span>
      </p>

      <KriTrend kri={kri} />
      <p className="muted kri-movement">
        6 periods · {MOVEMENT_LABEL[kri.movement]} · owned by {kri.owner_role}
      </p>

      <button type="button" className="kri-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? 'Hide definition' : 'How this is measured'}
      </button>
      {open && (
        <div className="kri-definition">
          <h4>Formula</h4>
          <p>{kri.formula_description}</p>
          <h4>Source</h4>
          <p>{kri.data_source}</p>
          <h4>Why it is tracked</h4>
          <p>{kri.rationale}</p>
          <h4>Current reading</h4>
          <p>{kri.current_detail}</p>
        </div>
      )}
    </article>
  )
}

export function Dashboard() {
  const { data, error, loading } = useAsync(() => api.kris(), [])
  const risks = useAsync(() => api.risks(), [])

  if (loading) return <p className="skeleton" role="status">Loading indicators…</p>
  if (error) return <p className="error">Could not load indicators: {error}</p>
  if (!data) return null

  const red = data.filter((k) => k.current_band === 'RED').length
  const worsening = data.filter((k) => k.movement === 'DETERIORATING').length

  return (
    <section>
      <div className="command-hero">
        <div className="command-intro">
          <span className="eyebrow">Governance, in perspective</span>
          <h1>
            A clearer view.
            <br />
            <span>A stronger position.</span>
          </h1>
          <p>Understand the exposure. Follow the evidence. Keep every decision accountable.</p>
          <div className="hero-actions">
            <Link className="primary-link" to="/risks">
              Explore risk register <span aria-hidden="true">↗</span>
            </Link>
            <Link to="/soa">Review controls →</Link>
          </div>
          <div className="hero-footnote">
            <span className="status-dot" />
            {risks.data?.length ?? '—'} recorded risks <span>·</span> {data.length} live indicators{' '}
            <span>·</span> Portfolio assessment
          </div>
        </div>
        {risks.data ? (
          <SecurityScene risks={risks.data} />
        ) : (
          <div className="skeleton">Loading risk model…</div>
        )}
      </div>
      <div className="section-heading">
        <div>
          <span className="eyebrow">Current position</span>
          <h2>Signals worth your attention</h2>
        </div>
        <span className="muted">Computed from your registers</span>
      </div>

      <div className="tiles">
        <div className="tile">
          <span className="tile-value">{data.length}</span>
          <span className="tile-label">indicators tracked</span>
        </div>
        <div className={`tile ${red > 0 ? 'tile-alert' : ''}`}>
          <span className="tile-value">{red}</span>
          <span className="tile-label">outside tolerance</span>
        </div>
        <div className={`tile ${worsening > 0 ? 'tile-todo' : ''}`}>
          <span className="tile-value">{worsening}</span>
          <span className="tile-label">getting worse</span>
        </div>
        <div className="tile">
          <span className="tile-value">{data.filter((k) => k.current_value === null).length}</span>
          <span className="tile-label">not measurable yet</span>
        </div>
      </div>

      {risks.data && <RiskHeatmap risks={risks.data} />}
      {risks.error && <p className="error">Risk heatmap unavailable: {risks.error}</p>}
      <div className="kri-grid">
        {data.map((kri) => (
          <KriCard key={kri.kri_ref} kri={kri} />
        ))}
      </div>
    </section>
  )
}
