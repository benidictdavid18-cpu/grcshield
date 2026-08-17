import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api, type RiskBand } from '../api'
import { useAsync } from '../useAsync'
import { STATUS_LABEL, TREATMENT_LABEL } from '../risk-labels'

const BAND_ORDER: RiskBand[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export function RiskRegister() {
  const risks = useAsync(() => api.risks(), [])
  const summary = useAsync(() => api.riskSummary(), [])
  const [onlyBreaching, setOnlyBreaching] = useState(false)
  const [category, setCategory] = useState('all')

  const categories = useMemo(() => {
    const seen = new Map<string, string>()
    for (const risk of risks.data ?? []) seen.set(risk.category, risk.category_label)
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [risks.data])

  const filtered = useMemo(() => {
    return (risks.data ?? []).filter((risk) => {
      if (onlyBreaching && risk.appetite.exceeds_appetite !== true) return false
      if (category !== 'all' && risk.category !== category) return false
      return true
    })
  }, [risks.data, onlyBreaching, category])

  if (risks.error) return <p className="error">Could not load the register: {risks.error}</p>

  return (
    <section>
      <h1>Risk register</h1>
      <p className="lede">
        Inherent and residual risk are scored independently. Residual is not derived from
        inherent by applying a control-effectiveness percentage — an analyst sets it directly
        and justifies it in writing.
      </p>

      {summary.data && (
        <div className="tiles">
          <div className="tile">
            <span className="tile-value">{summary.data.total}</span>
            <span className="tile-label">risks on the register</span>
          </div>
          <div className={`tile ${summary.data.exceeding_appetite > 0 ? 'tile-alert' : ''}`}>
            <span className="tile-value">{summary.data.exceeding_appetite}</span>
            <span className="tile-label">above category appetite</span>
          </div>
          <div className="tile">
            <span className="tile-value">
              {summary.data.by_residual_band.CRITICAL + summary.data.by_residual_band.HIGH}
            </span>
            <span className="tile-label">residual High or Critical</span>
          </div>
          <div className={`tile ${summary.data.justifications_outstanding > 0 ? 'tile-todo' : ''}`}>
            <span className="tile-value">{summary.data.justifications_outstanding}</span>
            <span className="tile-label">justifications outstanding</span>
          </div>
        </div>
      )}

      {summary.data && (
        <div className="band-legend">
          {summary.data.bands.map((band) => (
            <span key={band.band} className={`band band-${band.band.toLowerCase()}`}>
              {band.band.toLowerCase()} {band.min_score}–{band.max_score}
            </span>
          ))}
        </div>
      )}

      <div className="filters">
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="all">All categories</option>
          {categories.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={onlyBreaching}
            onChange={(event) => setOnlyBreaching(event.target.checked)}
          />
          Above appetite only
        </label>
        <span className="filter-count">{filtered.length} shown</span>
      </div>

      {risks.loading && <p className="empty">Loading register…</p>}

      <table className="register">
        <thead>
          <tr>
            <th>Ref</th>
            <th>Risk</th>
            <th>Category</th>
            <th className="num">Inherent</th>
            <th className="num">Residual</th>
            <th>Appetite</th>
            <th>Treatment</th>
          </tr>
        </thead>
        <tbody>
          {[...filtered]
            .sort(
              (a, b) =>
                BAND_ORDER.indexOf(a.residual.band) - BAND_ORDER.indexOf(b.residual.band) ||
                b.residual.score - a.residual.score,
            )
            .map((risk) => (
              <tr key={risk.risk_ref}>
                <td className="cell-ref">
                  <Link to={`/risks/${risk.risk_ref}`}>{risk.risk_ref}</Link>
                </td>
                <td>
                  {risk.title}
                  <span className="row-sub">
                    {STATUS_LABEL[risk.status]} · owned by {risk.owner_role}
                    {risk.justification_outstanding && (
                      <span className="tag tag-todo">justification outstanding</span>
                    )}
                    {risk.has_uncredited_controls && (
                      <span className="tag tag-warn">untested control linked</span>
                    )}
                  </span>
                </td>
                <td>{risk.category_label}</td>
                <td className="num">
                  <span className={`band band-${risk.inherent.band.toLowerCase()}`}>
                    {risk.inherent.score}
                  </span>
                </td>
                <td className="num">
                  <span className={`band band-${risk.residual.band.toLowerCase()}`}>
                    {risk.residual.score}
                  </span>
                </td>
                <td>
                  {risk.appetite.exceeds_appetite === null ? (
                    <span className="tag tag-warn">no appetite set</span>
                  ) : risk.appetite.exceeds_appetite ? (
                    <span className="tag tag-breach">
                      above {risk.appetite.max_acceptable_band?.toLowerCase()}
                    </span>
                  ) : (
                    <span className="tag tag-ok">within</span>
                  )}
                </td>
                <td>{TREATMENT_LABEL[risk.treatment_decision]}</td>
              </tr>
            ))}
        </tbody>
      </table>

      {!risks.loading && filtered.length === 0 && (
        <p className="empty">No risks match that filter.</p>
      )}
    </section>
  )
}
