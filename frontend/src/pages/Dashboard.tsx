import { useState } from 'react'

import { api, type Kri, type TrendPoint } from '../api'
import { useAsync } from '../useAsync'

const UNIT_SUFFIX: Record<string, string> = { PERCENT: '%', DAYS: 'd', COUNT: '' }

const MOVEMENT_LABEL: Record<string, string> = {
  IMPROVING: 'improving',
  DETERIORATING: 'getting worse',
  FLAT: 'unchanged',
  NO_TREND: 'no trend yet',
}

/** Six-month sparkline. Bars, not a line: the series is monthly observations rather
 *  than a continuous signal, and a line implies values between the points. */
function Sparkline({ points, direction }: { points: TrendPoint[]; direction: string }) {
  const values = points.map((p) => p.value).filter((v): v is number => v !== null)
  const max = Math.max(...values, 1)

  return (
    <div className="spark" role="img" aria-label={`Six-period trend, ${direction}`}>
      {points.map((point) => {
        const height = point.value === null ? 0 : Math.max(4, (point.value / max) * 100)
        return (
          <div key={point.period_end} className="spark-col" title={`${point.period_end}: ${point.value ?? 'not measured'}`}>
            <div
              className={`spark-bar spark-${point.band.toLowerCase()} ${point.is_current ? 'is-current' : ''}`}
              style={{ height: `${height}%` }}
            />
          </div>
        )
      })}
    </div>
  )
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

      <Sparkline points={kri.trend} direction={kri.movement} />
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

  if (loading) return <p className="empty">Loading indicators…</p>
  if (error) return <p className="error">Could not load indicators: {error}</p>
  if (!data) return null

  const red = data.filter((k) => k.current_band === 'RED').length
  const worsening = data.filter((k) => k.movement === 'DETERIORATING').length

  return (
    <section>
      <h1>Key risk indicators</h1>
      <p className="lede">
        Seven indicators, each with a formula precise enough that two people would compute
        the same number. Historical points are recorded observations; the current figure is
        computed from the registers on every page load, so the dashboard cannot drift away
        from the data behind it.
      </p>

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
          <span className="tile-value">
            {data.filter((k) => k.current_value === null).length}
          </span>
          <span className="tile-label">not measurable yet</span>
        </div>
      </div>

      <div className="kri-grid">
        {data.map((kri) => (
          <KriCard key={kri.kri_ref} kri={kri} />
        ))}
      </div>
    </section>
  )
}
