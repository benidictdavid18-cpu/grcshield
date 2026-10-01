import { type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { LiveTable } from './LiveTable'
import { useDrawerAccessibility } from './RecordDrawer'

function Detail({
  title,
  children,
  close,
}: {
  title: string
  children: ReactNode
  close: () => void
}) {
  const ref = useDrawerAccessibility(close)
  return (
    <aside ref={ref} className="drawer">
      <div className="drawer-head">
        <div>
          <span className="eyebrow">Sample / Portfolio Assessment</span>
          <h2>{title}</h2>
        </div>
        <button onClick={close} aria-label="Close register record">
          ×
        </button>
      </div>
      {children}
    </aside>
  )
}

/** Preserve the authored detail presentation while giving card registers a live index. */
export function RecordBrowser<T extends object>({
  id,
  rows,
  refKey,
  children,
}: {
  id: string
  rows: T[]
  refKey: keyof T
  children: (row: T) => ReactNode
}) {
  const [params, setParams] = useSearchParams()
  const key = `${id}.detail`
  const active = rows.find((row) => String(row[refKey]) === params.get(key))
  const choose = (value: string) =>
    setParams((old) => {
      const next = new URLSearchParams(old)
      if (value) next.set(key, value)
      else next.delete(key)
      return next
    })
  const field = (row: T, names: string[]) => {
    const data = row as Record<string, unknown>
    return String(
      names
        .map((name) => data[name])
        .find((value) => value !== undefined && value !== null && value !== '') ?? 'Not recorded',
    )
  }
  return (
    <>
      <LiveTable id={id}>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Record</th>
            <th>Owner</th>
            <th>Status / outcome</th>
            <th>Review / date</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row[refKey])}>
              <td>
                <button onClick={() => choose(String(row[refKey]))}>{String(row[refKey])}</button>
              </td>
              <td>
                {field(row, [
                  'title',
                  'risk_title',
                'process_name',
                'processing_activity',
                  'activity_name',
                  'name',
                  'scope',
                  'description',
                  'risk_ref',
                ])}
              </td>
              <td>
                {field(row, [
                  'owner',
                  'owner_role',
                  'risk_owner_role',
                  'lead_auditor',
                  'chair',
                  'controller',
                'assessed_by',
                'auditor',
                ])}
              </td>
              <td>
                {field(row, [
                  'status',
                  'outcome',
                  'residual_risk',
                  'overall_conclusion',
                  'lawful_basis',
                ])}
              </td>
              <td>
                {field(row, [
                  'review_date',
                  'next_review',
                  'expiry_date',
                  'target_date',
                  'audit_date',
                  'reviewed_on',
                  'identified_date',
                  'meeting_date',
                'last_reviewed',
                'assessment_date',
                'planned_start',
                ])}
              </td>
            </tr>
          ))}
        </tbody>
      </LiveTable>
      {active && (
        <Detail title={String(active[refKey])} close={() => choose('')}>
          {children(active)}
        </Detail>
      )}
    </>
  )
}
