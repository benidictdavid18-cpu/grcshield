import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { type Kri, type RiskSummary } from './api'

export function KriTrend({ kri }: { kri: Kri }) {
  const points = kri.trend.slice(-6)
  const max =
    Math.max(kri.green_threshold, kri.amber_threshold, ...points.map((p) => p.value ?? 0), 1) * 1.15
  const y = (value: number) => 132 - (value / max) * 112
  const x = (index: number) => 38 + index * 48
  const thresholds = [
    0,
    Math.min(kri.green_threshold, kri.amber_threshold),
    Math.max(kri.green_threshold, kri.amber_threshold),
    max,
  ]
  const bands =
    kri.direction === 'HIGHER_IS_BETTER' ? ['red', 'amber', 'green'] : ['green', 'amber', 'red']
  return (
    <figure className="trend-chart">
      <svg
        viewBox="0 0 320 164"
        role="img"
        aria-label={`${kri.name}: six-period trend with green and amber thresholds`}
      >
        {bands.map((band, i) => (
          <rect
            key={band}
            className={`chart-zone zone-${band}`}
            x="34"
            width="258"
            y={y(thresholds[i + 1])}
            height={y(thresholds[i]) - y(thresholds[i + 1])}
          />
        ))}
        {[kri.green_threshold, kri.amber_threshold].map((value, i) => (
          <g key={i}>
            <line className="threshold-line" x1="34" x2="292" y1={y(value)} y2={y(value)} />
            <text x="29" y={y(value) + 4} textAnchor="end">
              {value}
            </text>
          </g>
        ))}
        {points.map((point, i) => (
          <g key={point.period_end}>
            {i > 0 && point.value !== null && points[i - 1].value !== null && (
              <line
                className="trend-line"
                x1={x(i - 1)}
                y1={y(points[i - 1].value!)}
                x2={x(i)}
                y2={y(point.value)}
              />
            )}
            {point.value !== null && (
              <circle
                className={`trend-dot dot-${point.band.toLowerCase()}`}
                cx={x(i)}
                cy={y(point.value)}
                r={point.is_current ? 6 : 3.5}
              >
                <title>
                  {point.period_end}: {point.value}
                  {kri.unit === 'PERCENT' ? '%' : ''}
                  {point.is_current ? ' (current)' : ''}
                </title>
              </circle>
            )}
            <text x={x(i)} y="153" textAnchor="middle">
              {point.period_end.slice(5, 7)}/{point.period_end.slice(2, 4)}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="muted">
        Monthly observations; gaps mean not measured. Lines connect observations only.
      </figcaption>
      <details>
        <summary>Read chart values</summary>
        <ul>
          {points.map((p) => (
            <li key={p.period_end}>
              {p.period_end}: {p.value ?? 'not measured'} · {p.band.toLowerCase()}
              {p.is_current ? ' · current' : ''}
            </li>
          ))}
        </ul>
      </details>
    </figure>
  )
}

export function RiskHeatmap({ risks }: { risks: RiskSummary[] }) {
  const [selected, select] = useState('')
  const arrow = useId().replace(/:/g, '')
  const active = risks.find((risk) => risk.risk_ref === selected)
  return (
    <section className="heatmap-panel">
      <div className="section-heading">
        <div>
          <h2>Risk movement</h2>
          <p className="muted">Inherent ○ → residual ●. Select a risk to inspect its movement.</p>
        </div>
        <label>
          Highlight risk
          <select value={selected} onChange={(e) => select(e.target.value)}>
            <option value="">All {risks.length} risks</option>
            {risks.map((r) => (
              <option key={r.risk_ref} value={r.risk_ref}>
                {r.risk_ref} · {r.title}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="heatmap-layout">
        <svg
          viewBox="0 0 420 365"
          aria-label="Five by five risk heatmap: impact horizontally, likelihood vertically"
          role="img"
        >
          <defs>
            <marker
              id={arrow}
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
            </marker>
          </defs>
          {[1, 2, 3, 4, 5].flatMap((likelihood) =>
            [1, 2, 3, 4, 5].map((impact) => {
              const score = likelihood * impact
              return (
                <rect
                  key={`${likelihood}-${impact}`}
                  x={48 + (impact - 1) * 60}
                  y={20 + (5 - likelihood) * 60}
                  width="58"
                  height="58"
                  className={`heat-cell heat-${score >= 17 ? 'critical' : score >= 10 ? 'high' : score >= 5 ? 'medium' : 'low'}`}
                />
              )
            }),
          )}
          {[1, 2, 3, 4, 5].map((n) => (
            <g key={n}>
              <text x={78 + (n - 1) * 60} y="340" textAnchor="middle">
                {n}
              </text>
              <text x="32" y={55 + (5 - n) * 60}>
                {n}
              </text>
            </g>
          ))}
          <text x="196" y="360" textAnchor="middle">
            Impact →
          </text>
          <text transform="translate(15,175) rotate(-90)" textAnchor="middle">
            Likelihood →
          </text>
          {risks.map((risk, index) => {
            const dx = ((index % 4) - 1.5) * 9,
              dy = ((Math.floor(index / 4) % 4) - 1.5) * 9
            const x1 = 78 + (risk.inherent.impact - 1) * 60 + dx,
              y1 = 50 + (5 - risk.inherent.likelihood) * 60 + dy
            const x2 = 78 + (risk.residual.impact - 1) * 60 + dx,
              y2 = 50 + (5 - risk.residual.likelihood) * 60 + dy
            return (
              <g
                key={risk.risk_ref}
                className="heat-point"
                opacity={selected && selected !== risk.risk_ref ? 0.15 : 1}
                onClick={() => select(risk.risk_ref)}
              >
                <title>
                  {risk.risk_ref}: inherent {risk.inherent.score}, residual {risk.residual.score}
                </title>
                <line x1={x1} y1={y1} x2={x2} y2={y2} markerEnd={`url(#${arrow})`} />
                <circle cx={x1} cy={y1} r="5" fill="var(--surface)" />
                <circle cx={x2} cy={y2} r="3" fill="currentColor" />
              </g>
            )
          })}
        </svg>
        <div className="heatmap-detail">
          {active ? (
            <>
              <span className="eyebrow">Selected exposure</span>
              <h3>
                <Link to={`/risks/${active.risk_ref}`}>{active.risk_ref}</Link>
              </h3>
              <p>{active.title}</p>
              <p>
                {active.inherent.score} → <strong>{active.residual.score}</strong> ·{' '}
                {active.residual.band.toLowerCase()}
              </p>
              <p className="muted">{active.owner_role}</p>
            </>
          ) : (
            <>
              <h3>{risks.length} recorded exposures</h3>
              <p>
                Each arrow connects two independently assessed scores. Controls do not mechanically
                calculate the residual score.
              </p>
              <p className="muted">
                Overlapping points are offset within their cell. Use the selector to isolate any
                risk.
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
