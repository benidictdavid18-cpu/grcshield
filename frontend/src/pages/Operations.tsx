import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiValidationError } from '../api'
import { useAuth } from '../auth'
import { FieldError, UnplacedErrors } from '../editing'
import { LiveTable } from '../LiveTable'
import { RecordFields, useDrawerAccessibility } from '../RecordDrawer'
import { useAsync } from '../useAsync'

const MODULES = [
  [
    'incidents',
    'Events & incidents',
    '/incidents',
    'Record an event with its risk, control and source, then retain every triage and response decision.',
  ],
  [
    'suppliers',
    'Suppliers',
    '/suppliers',
    'Review service dependencies, agreements and supplier actions.',
  ],
  [
    'obligations',
    'Obligations',
    '/obligations',
    'Applicability remains an authorized legal decision. Draft entries are not determinations.',
  ],
  [
    'context',
    'Context',
    '/isms/context',
    'Context issues, interested parties and process boundaries.',
  ],
  [
    'documents',
    'Documents',
    '/documents',
    'Controlled documents retain revisions and publication decisions.',
  ],
  [
    'treatment',
    'Treatment plans',
    '/treatment-plans',
    'Owned commitments and milestones supporting risk treatment.',
  ],
  [
    'plans',
    'Objectives & changes',
    '/isms/plans',
    'Management objectives and planned changes, with retained decisions.',
  ],
  [
    'assurance',
    'Assurance',
    '/isms/assurance/cycles',
    'Audit and management review cycles with retained inputs and actions.',
  ],
  [
    'competence',
    'Competence',
    '/people/requirements',
    'Role requirements; no invented personnel assessments.',
  ],
  [
    'communications',
    'Communications',
    '/people/communications',
    'Planned audiences, methods and evidence of delivery.',
  ],
  [
    'monitoring',
    'Measurement plans',
    '/monitoring/plans',
    'Measurement definitions, collection responsibilities and review dates.',
  ],
  [
    'observations',
    'Observations',
    '/monitoring/observations',
    'Measured values with the definition and evidence that supported them.',
  ],
  [
    'revisions',
    'Operational revisions',
    '/operations/revisions',
    'Proposed register changes remain drafts until reviewed.',
  ],
  [
    'coverage',
    'Operational evidence',
    '/operations/coverage',
    'Evidence coverage linked to the relevant internal control.',
  ],
  [
    'exercises',
    'Continuity exercises',
    '/operations/exercises',
    'Observed recovery results, retained alongside the original targets.',
  ],
  [
    'reassessments',
    'Reassessment queue',
    '/reassessments',
    'Review records affected by changed test evidence.',
  ],
  [
    'notifications',
    'My notifications',
    '/notifications',
    'Acknowledgement marks a reminder as read; it does not close the underlying obligation.',
  ],
] as const
type Row = Record<string, unknown>
function identity(row: Row) {
  if ('dedup_key' in row) return `N-${row.id}`
  if ('content' in row && 'record_ref' in row) return `${row.record_ref} / v${row.revision}`
  return String(
    row.event_ref ??
      row.supplier_ref ??
      row.obligation_ref ??
      row.context_ref ??
      row.document_ref ??
      row.plan_ref ??
      row.cycle_ref ??
      row.requirement_ref ??
      row.communication_ref ??
      row.record_ref ??
      row.kri_ref ??
      row.id ??
      'Record',
  )
}
function value(row: Row, keys: string[]) {
  return String(
    keys
      .map((key) => row[key])
      .find((entry) => entry !== null && entry !== undefined && entry !== '') ?? 'Not recorded',
  )
}

function Detail({ row, onClose }: { row: Row; onClose: () => void }) {
  const ref = useDrawerAccessibility(onClose)
  return (
    <aside ref={ref} className="drawer">
      <div className="drawer-head">
        <div>
          <span className="eyebrow">Sample / Portfolio Assessment</span>
          <h2>{identity(row)}</h2>
        </div>
        <button onClick={onClose} aria-label="Close record details">
          ×
        </button>
      </div>
      <RecordFields value={row} />
    </aside>
  )
}

const EVENT_FIELDS = [
  'reference',
  'title',
  'description',
  'source',
  'occurred_on',
  'reported_on',
  'owner',
  'risk_ref',
  'control_ref',
  'finding_ref',
]
function EventForm({ onSaved }: { onSaved: () => void }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiValidationError | null>(null)
  const [message, setMessage] = useState('')
  return (
    <section className="edit-panel">
      <button aria-expanded={open} onClick={() => setOpen(!open)}>
        Record security event
      </button>
      {open && (
        <form
          className="edit-form"
          onSubmit={async (event) => {
            event.preventDefault()
            setBusy(true)
            setError(null)
            setMessage('')
            const form = new FormData(event.currentTarget)
            const { reference, ...body } = Object.fromEntries(form.entries())
            if (!body.finding_ref) delete body.finding_ref
            try {
              await api.write('POST', `/incidents/${encodeURIComponent(String(reference))}`, body)
              setOpen(false)
              onSaved()
            } catch (failure) {
              if (failure instanceof ApiValidationError) setError(failure)
              else setMessage((failure as Error).message)
            } finally {
              setBusy(false)
            }
          }}
        >
          <p className="muted">
            Capture the observation. Classification and response decisions belong to the retained
            incident timeline.
          </p>
          <div className="edit-fields">
            {EVENT_FIELDS.map((field) => (
              <label key={field}>
                {field.replace(/_/g, ' ')}
                {field === 'description' ? (
                  <textarea name={field} required />
                ) : (
                  <input
                    name={field}
                    required={field !== 'finding_ref'}
                    type={field.endsWith('_on') ? 'date' : 'text'}
                  />
                )}
                <FieldError refusal={error} field={field} />
              </label>
            ))}
          </div>
          <UnplacedErrors refusal={error} shown={EVENT_FIELDS} />
          {(message || (error && !error.fieldErrors.length)) && (
            <p className="error" role="alert">
              {message || error?.message}
            </p>
          )}
          <button type="submit" disabled={busy}>
            {busy ? 'Saving…' : 'Save event'}
          </button>
        </form>
      )}
    </section>
  )
}

export function Operations() {
  const [params, setParams] = useSearchParams()
  const module = MODULES.find(([key]) => key === params.get('module')) ?? MODULES[0]
  const [version, setVersion] = useState(0)
  const state = useAsync(() => api.read<Row[]>(module[2]), [module[2], version])
  const [optimistic, setOptimistic] = useState<Record<string, boolean>>({})
  const [pending, setPending] = useState<Record<string, boolean>>({})
  const [writeError, setWriteError] = useState('')
  const { session } = useAuth()
  const selected = state.data?.find((row) => identity(row) === params.get('item'))
  const select = (key: string, entry: string) =>
    setParams((old) => {
      const next = new URLSearchParams(old)
      if (entry) next.set(key, entry)
      else next.delete(key)
      return next
    })
  return (
    <section>
      <span className="eyebrow">Management system workspace</span>
      <h1>Operations & assurance</h1>
      <p className="lede">
        Follow a record from its source through review, evidence and action. Sample / Portfolio
        Assessment.
      </p>
      <div className="workspace-tabs" aria-label="Operational registers">
        {MODULES.map(([key, label]) => (
          <button
            key={key}
            className={module[0] === key ? 'active' : ''}
            aria-pressed={module[0] === key}
            onClick={() => {
              setWriteError('')
              setParams((old) => {
                const next = new URLSearchParams(old)
                next.set('module', key)
                next.delete('item')
                return next
              })
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <h2>{module[1]}</h2>
      <p className="muted">{module[3]}</p>
      {module[0] === 'incidents' && session?.canWrite && (
        <EventForm onSaved={() => setVersion((v) => v + 1)} />
      )}
      {state.loading && (
        <div className="skeleton" role="status">
          Loading {module[1].toLowerCase()}…
        </div>
      )}
      {state.error && (
        <div className="error" role="alert">
          <p>{state.error}</p>
          <button onClick={() => setVersion((v) => v + 1)}>Retry loading</button>
        </div>
      )}
      {writeError && (
        <p className="error" role="alert">
          {writeError}
        </p>
      )}
      {state.data && (
        <LiveTable id={`operations-${module[0]}`}>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Record</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Review / due date</th>
            </tr>
          </thead>
          <tbody>
            {state.data.map((row) => {
              const ref = identity(row)
              return (
                <tr key={ref}>
                  <td>
                    <button onClick={() => select('item', ref)}>{ref}</button>
                  </td>
                  <td>
                    {value(row, [
                      'title',
                      'name',
                      'message',
                      'topic',
                      'role',
                      'record_ref',
                      'method',
                    ])}
                  </td>
                  <td>
                    {value(row, [
                      'owner',
                      'evaluation_owner',
                      'collection_owner',
                      'owner_label',
                      'actor',
                    ])}
                  </td>
                  <td>
                    {optimistic[ref]
                      ? 'ACKNOWLEDGED'
                      : value(row, ['status', 'applicability', 'kind'])}
                    {module[0] === 'notifications' &&
                      row.status !== 'ACKNOWLEDGED' &&
                      !optimistic[ref] && (
                        <button
                          disabled={pending[ref]}
                          onClick={async () => {
                            setOptimistic((old) => ({ ...old, [ref]: true }))
                            setPending((old) => ({ ...old, [ref]: true }))
                            setWriteError('')
                            try {
                              await api.write('POST', `/notifications/${row.id}/acknowledge`)
                              setVersion((v) => v + 1)
                            } catch (error) {
                              setOptimistic((old) => ({ ...old, [ref]: false }))
                              setWriteError(
                                `Acknowledgement was not saved: ${(error as Error).message}`,
                              )
                            } finally {
                              setPending((old) => ({ ...old, [ref]: false }))
                            }
                          }}
                        >
                          Acknowledge
                        </button>
                      )}
                  </td>
                  <td>
                    {value(row, [
                      'review_date',
                      'next_date',
                      'due_on',
                      'due_date',
                      'occurred_on',
                      'reported_on',
                    ])}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </LiveTable>
      )}
      {state.data?.length === 0 && (
        <p className="muted">
          No {module[1].toLowerCase()} have been recorded.{' '}
          {module[0] === 'notifications'
            ? 'There are no reminders assigned to your account.'
            : 'A maintainer can create the source record through its rule-checked workflow.'}
        </p>
      )}
      {selected && <Detail row={selected} onClose={() => select('item', '')} />}
    </section>
  )
}
