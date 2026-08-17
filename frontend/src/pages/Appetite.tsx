import { api } from '../api'
import { useAsync } from '../useAsync'

export function Appetite() {
  const { data, error, loading } = useAsync(() => api.appetite(), [])

  if (loading) return <p className="empty">Loading appetite…</p>
  if (error) return <p className="error">Could not load appetite: {error}</p>
  if (!data) return null

  return (
    <section>
      <h1>Risk appetite</h1>
      <p className="lede">
        Appetite is set per category, not once for the whole organisation. A single global
        number would say the business tolerates the same exposure to a privacy breach as to a
        laptop running an old OS. Each ceiling is approved by the person who answers for the
        consequence — none of them is the security function.
      </p>

      <table className="register">
        <thead>
          <tr>
            <th>Category</th>
            <th>Maximum acceptable</th>
            <th>Approved by</th>
            <th>Rationale</th>
            <th>Last reviewed</th>
          </tr>
        </thead>
        <tbody>
          {data.map((entry) => (
            <tr key={entry.category}>
              <td>{entry.category_label}</td>
              <td>
                <span className={`band band-${entry.max_acceptable_band.toLowerCase()}`}>
                  {entry.max_acceptable_band.toLowerCase()}
                </span>
              </td>
              <td>{entry.approver_role}</td>
              <td className="rationale-cell">{entry.rationale}</td>
              <td>{entry.last_reviewed ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
