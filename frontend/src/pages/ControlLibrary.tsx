import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api, type Control, type MappingRelationship } from '../api'
import { useAsync } from '../useAsync'

type ScopeFilter = 'all' | 'in' | 'out'

const RELATIONSHIP_HINT: Record<MappingRelationship, string> = {
  EQUIVALENT: 'Substantially satisfies this criterion on its own.',
  PARTIAL: 'Satisfies part of this criterion; other controls cover the rest.',
  SUPPORTING: 'Contributes evidence but is not the primary control tested.',
}

function ControlDrawer({ framework, controlRef, onClose }: {
  framework: string
  controlRef: string
  onClose: () => void
}) {
  const { data, error, loading } = useAsync(
    () => api.control(framework, controlRef),
    [framework, controlRef],
  )

  return (
    <aside className="drawer">
      <div className="drawer-head">
        <h2>{controlRef}</h2>
        <button type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      {loading && <p className="empty">Loading…</p>}
      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <p className="drawer-title">{data.title}</p>
          <p className="card-meta">
            {data.group_ref} {data.group_title}
          </p>

          <div className={`scope-block ${data.in_scope ? 'is-in' : 'is-out'}`}>
            <strong>{data.in_scope ? 'In scope' : 'Provisionally excluded'}</strong>
            {data.scope_note && <p>{data.scope_note}</p>}
            {data.in_scope && (
              <p className="muted">
                The Statement of Applicability records the formal inclusion justification and
                implementation status.
              </p>
            )}
          </div>

          <h3>SOC 2 coverage</h3>
          {data.mappings.length === 0 ? (
            <p className="muted">
              No mapping. Either the control is out of scope, or its natural SOC 2 counterpart sits
              in a Trust Services category FinFlow has not elected.
            </p>
          ) : (
            <ul className="mapping-list">
              {data.mappings.map((mapping) => (
                <li key={mapping.control_ref}>
                  <div className="mapping-head">
                    <code>{mapping.control_ref}</code>
                    <span className={`rel rel-${mapping.relationship_type.toLowerCase()}`}>
                      {mapping.relationship_type.toLowerCase()}
                    </span>
                  </div>
                  <p>{mapping.title}</p>
                  <p className="muted">{RELATIONSHIP_HINT[mapping.relationship_type]}</p>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </aside>
  )
}

export function ControlLibrary() {
  const [searchParams, setSearchParams] = useSearchParams()
  const framework = searchParams.get('framework') ?? 'ISO27001_2022'
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState<ScopeFilter>('all')
  const [selected, setSelected] = useState<string | null>(null)

  const detail = useAsync(() => api.framework(framework), [framework])
  const controls = useAsync(() => api.controls(framework), [framework])

  const filtered = useMemo(() => {
    const rows = controls.data ?? []
    const needle = query.trim().toLowerCase()
    return rows.filter((control) => {
      if (scope === 'in' && !control.in_scope) return false
      if (scope === 'out' && control.in_scope) return false
      if (!needle) return true
      return (
        control.control_ref.toLowerCase().includes(needle) ||
        control.title.toLowerCase().includes(needle)
      )
    })
  }, [controls.data, query, scope])

  const grouped = useMemo(() => {
    const map = new Map<string, { title: string; rows: Control[] }>()
    for (const control of filtered) {
      const bucket = map.get(control.group_ref) ?? { title: control.group_title, rows: [] }
      bucket.rows.push(control)
      map.set(control.group_ref, bucket)
    }
    return [...map.entries()]
  }, [filtered])

  if (controls.error) return <p className="error">Could not load controls: {controls.error}</p>

  const summary = detail.data

  return (
    <section className="library">
      <div className="library-main">
        <h1>Control library</h1>

        <div className="framework-switch">
          {['ISO27001_2022', 'SOC2_TSC'].map((code) => (
            <button
              key={code}
              type="button"
              className={code === framework ? 'active' : ''}
              onClick={() => {
                setSelected(null)
                setSearchParams({ framework: code })
              }}
            >
              {code === 'ISO27001_2022' ? 'ISO/IEC 27001:2022' : 'SOC 2 TSC'}
            </button>
          ))}
        </div>

        {summary && (
          <div className="summary-strip">
            {summary.groups.map((group) => (
              <div key={group.group_ref}>
                <span className="summary-ref">{group.group_ref}</span>
                <span className="summary-title">{group.group_title}</span>
                <span className="summary-count">
                  {group.in_scope} in scope
                  {group.out_of_scope > 0 && ` · ${group.out_of_scope} excluded`}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="filters">
          <input
            type="search"
            placeholder="Filter by reference or title…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="segmented">
            {(['all', 'in', 'out'] as ScopeFilter[]).map((option) => (
              <button
                key={option}
                type="button"
                className={option === scope ? 'active' : ''}
                onClick={() => setScope(option)}
              >
                {option === 'all' ? 'All' : option === 'in' ? 'In scope' : 'Excluded'}
              </button>
            ))}
          </div>
          <span className="filter-count">{filtered.length} shown</span>
        </div>

        {controls.loading && <p className="empty">Loading controls…</p>}

        {grouped.map(([groupRef, group]) => (
          <div key={groupRef} className="control-group">
            <h2>
              {groupRef} <span>{group.title}</span>
            </h2>
            <table>
              <tbody>
                {group.rows.map((control) => (
                  <tr
                    key={control.control_ref}
                    className={selected === control.control_ref ? 'selected' : ''}
                  >
                    <td className="cell-ref">
                      {/* A real button rather than a click handler on the row, so the
                          library is reachable by keyboard and announces each control. */}
                      <button
                        type="button"
                        onClick={() => setSelected(control.control_ref)}
                        aria-expanded={selected === control.control_ref}
                      >
                        {control.control_ref}
                      </button>
                    </td>
                    <td>{control.title}</td>
                    <td className="cell-scope">
                      <span className={control.in_scope ? 'pill pill-in' : 'pill pill-out'}>
                        {control.in_scope ? 'in scope' : 'excluded'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

        {!controls.loading && filtered.length === 0 && (
          <p className="empty">No controls match that filter.</p>
        )}
      </div>

      {selected && (
        <ControlDrawer
          framework={framework}
          controlRef={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </section>
  )
}
