import { useMemo, useState } from 'react'

import { api, openReport, type ImplementationStatus, type SoASummary } from '../api'
import { useAsync } from '../useAsync'
import { IMPLEMENTATION_LABEL } from '../risk-labels'
import { SoADrawer } from './SoADrawer'

type ApplicabilityFilter = 'all' | 'applicable' | 'excluded' | 'gaps'
type SortKey = 'ref' | 'status' | 'owner'

const STATUS_ORDER: ImplementationStatus[] = [
  'NOT_IMPLEMENTED',
  'PARTIALLY_IMPLEMENTED',
  'IMPLEMENTED',
]

function refOrder(controlRef: string): number {
  const [theme, number] = controlRef.replace('A.', '').split('.')
  return Number(theme) * 1000 + Number(number)
}

export function SoA() {
  const overview = useAsync(() => api.soaOverview(), [])
  const entries = useAsync(() => api.soa(), [])
  const [applicability, setApplicability] = useState<ApplicabilityFilter>('all')
  const [theme, setTheme] = useState('all')
  const [query, setQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('ref')
  const [selected, setSelected] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const rows = (entries.data ?? []).filter((entry) => {
      if (applicability === 'applicable' && !entry.applicable) return false
      if (applicability === 'excluded' && entry.applicable) return false
      if (applicability === 'gaps' && !entry.is_gap) return false
      if (theme !== 'all' && entry.theme !== theme) return false
      const needle = query.trim().toLowerCase()
      if (!needle) return true
      return (
        entry.control_ref.toLowerCase().includes(needle) ||
        entry.control_title.toLowerCase().includes(needle)
      )
    })

    return [...rows].sort((a, b) => {
      if (sortKey === 'status') {
        const delta =
          STATUS_ORDER.indexOf(a.implementation_status) -
          STATUS_ORDER.indexOf(b.implementation_status)
        if (delta !== 0) return delta
      }
      if (sortKey === 'owner') {
        const delta = a.owner.localeCompare(b.owner)
        if (delta !== 0) return delta
      }
      return refOrder(a.control_ref) - refOrder(b.control_ref)
    })
  }, [entries.data, applicability, theme, query, sortKey])

  const grouped = useMemo(() => {
    const map = new Map<string, SoASummary[]>()
    for (const entry of filtered) {
      map.set(entry.theme, [...(map.get(entry.theme) ?? []), entry])
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [filtered])

  if (entries.error) return <p className="error">Could not load the SoA: {entries.error}</p>

  const summary = overview.data

  return (
    <section className="library">
      <div className="library-main">
        <h1>Statement of Applicability</h1>
        <p className="lede">
          Required by ISO/IEC 27001:2022 Clause 6.1.3 d). One row for every Annex A control,
          each with an applicability decision and a justification that names a driver — a risk,
          a law, or a contract. "Required by ISO 27001" is circular and the API rejects it.
        </p>

        {summary && (
          <>
            <div className="tiles">
              <div className="tile">
                <span className="tile-value">{summary.applicable}</span>
                <span className="tile-label">applicable of {summary.total_controls}</span>
              </div>
              <div className="tile">
                <span className="tile-value">{summary.excluded}</span>
                <span className="tile-label">excluded</span>
              </div>
              <div className="tile">
                <span className="tile-value">{summary.implemented}</span>
                <span className="tile-label">implemented</span>
              </div>
              <div className="tile">
                <span className="tile-value">{summary.percent_implemented}%</span>
                <span className="tile-label">of applicable controls</span>
              </div>
              <div className={`tile ${summary.gaps > 0 ? 'tile-alert' : ''}`}>
                <span className="tile-value">{summary.gaps}</span>
                <span className="tile-label">gaps</span>
              </div>
            </div>

            <div className="quality-strip">
              <span>
                <strong>{summary.open_remediation}</strong> open remediation
              </span>
              <span className={summary.overdue_remediation > 0 ? 'is-bad' : ''}>
                <strong>{summary.overdue_remediation}</strong> overdue
              </span>
              <span className={summary.expired_evidence > 0 ? 'is-bad' : ''}>
                <strong>{summary.expired_evidence}</strong> expired evidence
              </span>
              <span className={summary.implemented_without_evidence > 0 ? 'is-bad' : ''}>
                <strong>{summary.implemented_without_evidence}</strong> implemented without
                evidence
              </span>
              <span className={summary.justifications_outstanding > 0 ? 'is-todo' : ''}>
                <strong>{summary.justifications_outstanding}</strong> justifications outstanding
              </span>
              <button
                type="button"
                className="pdf-link"
                onClick={() => openReport(api.soaReportUrl())}
              >
                SoA + Gap Analysis PDF →
              </button>
            </div>
          </>
        )}

        <div className="filters">
          <input
            type="search"
            placeholder="Filter by reference or title…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="segmented">
            {(['all', 'applicable', 'excluded', 'gaps'] as ApplicabilityFilter[]).map((option) => (
              <button
                key={option}
                type="button"
                className={option === applicability ? 'active' : ''}
                onClick={() => setApplicability(option)}
              >
                {option === 'all'
                  ? 'All'
                  : option === 'applicable'
                    ? 'Applicable'
                    : option === 'excluded'
                      ? 'Excluded'
                      : 'Gaps'}
              </button>
            ))}
          </div>
          <select value={theme} onChange={(event) => setTheme(event.target.value)}>
            <option value="all">All themes</option>
            {(summary?.themes ?? []).map((entry) => (
              <option key={entry.theme} value={entry.theme}>
                {entry.theme} {entry.theme_title}
              </option>
            ))}
          </select>
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            <option value="ref">Sort by reference</option>
            <option value="status">Sort by status</option>
            <option value="owner">Sort by owner</option>
          </select>
          <span className="filter-count">{filtered.length} shown</span>
        </div>

        {entries.loading && <p className="empty">Loading the SoA…</p>}

        {grouped.map(([themeRef, rows]) => {
          const themeSummary = summary?.themes.find((t) => t.theme === themeRef)
          return (
            <div key={themeRef} className="control-group">
              <h2>
                {themeRef} <span>{themeSummary?.theme_title ?? ''}</span>
                {themeSummary && (
                  <span className="theme-counts">
                    {themeSummary.implemented}/{themeSummary.applicable} implemented
                    {themeSummary.excluded > 0 && ` · ${themeSummary.excluded} excluded`}
                  </span>
                )}
              </h2>
              <table>
                <tbody>
                  {rows.map((entry) => (
                    <tr
                      key={entry.control_ref}
                      className={selected === entry.control_ref ? 'selected' : ''}
                    >
                      <td className="cell-ref">
                        <button
                          type="button"
                          onClick={() => setSelected(entry.control_ref)}
                          aria-expanded={selected === entry.control_ref}
                        >
                          {entry.control_ref}
                        </button>
                      </td>
                      <td>
                        {entry.control_title}
                        <span className="row-sub">
                          {entry.owner}
                          {entry.justification_outstanding && (
                            <span className="tag tag-todo">justification outstanding</span>
                          )}
                          {entry.has_expired_evidence && (
                            <span className="tag tag-warn">expired evidence</span>
                          )}
                        </span>
                      </td>
                      <td className="cell-links">
                        <span title="Linked risks">R {entry.linked_risk_count}</span>
                        <span title="Linked internal controls">C {entry.linked_control_count}</span>
                        <span title="Linked evidence">E {entry.linked_evidence_count}</span>
                        <span title="Open remediation">M {entry.open_remediation_count}</span>
                      </td>
                      <td className="cell-scope">
                        <span className={entry.applicable ? 'pill pill-in' : 'pill pill-out'}>
                          {entry.applicable ? 'applicable' : 'excluded'}
                        </span>
                      </td>
                      <td className="cell-status">
                        <span
                          className={`impl impl-${entry.implementation_status.toLowerCase()}`}
                        >
                          {IMPLEMENTATION_LABEL[entry.implementation_status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        })}

        {!entries.loading && filtered.length === 0 && (
          <p className="empty">No controls match that filter.</p>
        )}
      </div>

      {selected && <SoADrawer controlRef={selected} onClose={() => setSelected(null)} />}
    </section>
  )
}
