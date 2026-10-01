import { useId, useState } from 'react'
import contracts from './workflow-contracts.json'
import { api, ApiValidationError } from './api'
import { RecordFields } from './RecordDrawer'

type Values = Record<string, unknown>
export type Schema = {
  type?: string; title?: string; format?: string; enum?: (string | number)[]
  properties?: Record<string, Schema>; required?: string[]; items?: Schema
  anyOf?: Schema[]; default?: unknown; minimum?: number; maximum?: number
  minLength?: number; maxLength?: number; variants?: Record<string, Schema>
}
type Contract = { group: string; path: string; method: 'POST' | 'PUT' | 'PATCH'; parameters: { name: string; schema: Schema }[]; body: Schema }
const workflows = contracts as unknown as Contract[]
const words = (value: string) => value.replace(/[_-]/g, ' ').replace(/\bisms\b/gi, 'ISMS').replace(/\bsoa\b/gi, 'SoA')
const TITLES: Record<string, string> = {
  '/incidents/{ref}': 'Record security event',
  '/incidents/{ref}/timeline': 'Record triage or response decision',
  '/suppliers/{ref}': 'Create or edit supplier',
  '/suppliers/{ref}/reviews': 'Record supplier review',
  '/suppliers/{ref}/reviews/{review_id}/complete': 'Complete supplier action',
  '/obligations/{ref}': 'Create or edit obligation',
  '/obligations/{ref}/decisions': 'Record applicability or evaluation decision',
  '/isms/context/{ref}': 'Create or edit context entry',
  '/isms/context/{ref}/review': 'Review context entry',
  '/isms/scope-revisions': 'Create scope revision',
  '/isms/scope-revisions/{scope_id}/approve': 'Approve scope revision',
  '/documents/{ref}': 'Create or edit document details',
  '/documents/{ref}/revisions': 'Write document revision',
  '/document-revisions/{revision_id}/{action}': 'Approve, publish or withdraw revision',
  '/document-revisions/{revision_id}/acknowledgements': 'Acknowledge published revision',
  '/treatment-plans/{ref}': 'Create or edit treatment plan',
  '/treatment-plans/{ref}/milestones/{milestone_ref}': 'Create or edit milestone',
  '/treatment-plans/{ref}/approve': 'Approve treatment plan',
  '/treatment-plans/{ref}/close': 'Close treatment plan',
  '/treatment-plans/{ref}/cancel': 'Cancel treatment plan',
  '/treatment-milestones/{milestone_id}/complete': 'Complete milestone',
  '/isms/plans/{ref}': 'Create or edit objective or change plan',
  '/isms/plans/{ref}/approve': 'Approve objective or change plan',
  '/isms/plans/{ref}/implement': 'Record plan implementation',
  '/isms/plans/{ref}/evaluations': 'Evaluate plan outcome',
  '/isms/plans/{ref}/cancel': 'Cancel objective or change plan',
  '/isms/assurance/programmes/{ref}': 'Create or edit audit programme',
  '/isms/assurance/audits/{ref}': 'Create or edit audit cycle',
  '/isms/assurance/reviews/{ref}': 'Create or edit management review',
  '/isms/assurance/cycles/{ref}/inputs/{category}': 'Record review input',
  '/isms/assurance/cycles/{ref}/actions': 'Assign review action',
  '/isms/assurance/cycles/{ref}/complete': 'Complete assurance cycle',
  '/isms/assurance/actions/{ref}/complete': 'Complete assurance action',
  '/isms/assurance/nonconformities/{ref}': 'Create or edit nonconformity',
  '/isms/assurance/nonconformities/{ref}/verifications': 'Verify corrective action',
  '/people/requirements/{ref}': 'Create or edit competence requirement',
  '/people/requirements/{ref}/evaluations': 'Evaluate competence',
  '/people/communications/{ref}': 'Create or edit communication plan',
  '/people/communications/{ref}/deliver': 'Record communication delivery',
  '/monitoring/plans/{ref}': 'Create or edit measurement plan',
  '/monitoring/plans/{ref}/observations': 'Record measurement',
  '/monitoring/observations/{observation_id}/evaluate': 'Evaluate observation',
  '/operations/revisions': 'Propose asset, processing, privacy or continuity revision',
  '/operations/revisions/{revision_id}/review': 'Review operational revision',
  '/operations/reassessments/{task_id}/resolve': 'Resolve operational reassessment',
  '/operations/coverage': 'Record operational evidence coverage',
  '/operations/exercises/{ref}': 'Record continuity exercise',
  '/reassessments/{item_id}/resolve': 'Resolve test-triggered reassessment',
  '/notifications/routing': 'Assign reminder recipient',
  '/notifications/run': 'Collect due reminders',
  '/notifications/{notification_id}/acknowledge': 'Acknowledge reminder',
  '/evidence/{evidence_ref}/attachments': 'Attach evidence file',
  '/evidence-attachments/{attachment_id}/retention': 'Extend retention or change legal hold',
  '/evidence-attachments/{attachment_id}/purge': 'Purge eligible evidence bytes',
  '/soa-releases': 'Create SoA release',
  '/soa-releases/{release_id}/approve': 'Approve SoA release',
  '/risk-exceptions': 'Request risk acceptance',
  '/risk-exceptions/{exception_ref}/decisions': 'Approve, reject or withdraw acceptance',
  '/acceptance-authorities': 'Assign acceptance authority',
  '/risks/{risk_ref}/controls/{control_ref}/proof': 'Bind risk claim to a workpaper',
  '/control-tests': 'Record control test',
  '/control-tests/{test_ref}/disposition': 'Supersede or withdraw workpaper',
}

export function resolveSchema(schema: Schema, root: Values): Schema {
  if (schema.variants) return schema.variants[String(root.kind)] ?? { type: 'object', properties: {} }
  if (schema.anyOf) return { ...schema, ...schema.anyOf.find((s) => s.type !== 'null'), anyOf: undefined }
  return schema
}

// Only values the author entered are sent. In particular, no rating, approval or date
// is chosen on their behalf. Pydantic applies its declared defaults on the server.
export function payloadFor(schema: Schema, values: Values): Values {
  return Object.fromEntries(Object.entries(schema.properties ?? {}).flatMap(([key, raw]) => {
    const spec = resolveSchema(raw, values)
    const value = values[key]
    if (value === undefined || value === '') {
      if (schema.required?.includes(key) && raw.anyOf?.some((s) => s.type === 'null')) return [[key, null]]
      return []
    }
    if (spec.type === 'object') return [[key, payloadFor(spec, value as Values)]]
    return [[key, value]]
  }))
}

function Fields({ schema, values, onChange, root, prefix = '', errors }: {
  schema: Schema; values: Values; onChange: (v: Values) => void; root: Values; prefix?: string; errors: Record<string, string>
}) {
  const id = useId()
  return <div className="edit-fields">{Object.entries(schema.properties ?? {}).map(([key, raw]) => {
    const spec = resolveSchema(raw, root)
    const name = prefix + key
    const inputId = `${id}-${name}`
    const error = errors[name]
    const required = Boolean(schema.required?.includes(key)) && !raw.anyOf?.some((s) => s.type === 'null')
    const value = values[key]
    const update = (next: unknown) => onChange({ ...values, [key]: next, ...(key === 'kind' && schema.properties?.content?.variants ? { content: {} } : {}) })
    const props = { id: inputId, required, 'aria-invalid': Boolean(error), 'aria-describedby': error ? `${inputId}-error` : undefined }
    if (key === 'content_base64') return <label key={key} htmlFor={inputId}>Evidence file
      <input {...props} type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.json" onChange={async (event) => {
        const file = event.target.files?.[0]
        if (!file) return
        if (file.size > 8 * 1024 * 1024) { event.target.setCustomValidity('Choose a file no larger than 8 MiB.'); return }
        event.target.setCustomValidity('')
        const bytes = new Uint8Array(await file.arrayBuffer())
        let binary = ''
        for (const byte of bytes) binary += String.fromCharCode(byte)
        onChange({ ...values, content_base64: btoa(binary), filename: file.name, content_type: file.type || 'text/plain' })
      }} />{error && <span id={`${inputId}-error`} role="alert">{error}</span>}</label>
    if (spec.type === 'object') return <fieldset key={key} className="workflow-nested"><legend>{words(key)}</legend>
      {raw.variants && !root.kind && <p>Select the record kind above to enter its fields.</p>}
      <Fields schema={spec} values={(value as Values) ?? {}} onChange={update} root={root} prefix={`${name}.`} errors={errors} />
      {error && <p role="alert">{error}</p>}
    </fieldset>
    const label = key === 'expected_revision' ? 'Current revision (prevents overwriting newer changes)' : words(key)
    let control
    if (spec.enum || spec.type === 'boolean') {
      const choices = spec.enum ?? ['true', 'false']
      control = <select {...props} value={value === undefined ? '' : String(value)} onChange={(e) => update(e.target.value === '' ? undefined : spec.type === 'boolean' ? e.target.value === 'true' : e.target.value)}>
        <option value="">Choose…</option>{choices.map((choice) => <option key={String(choice)} value={String(choice)}>{spec.type === 'boolean' ? choice === 'true' ? 'Yes' : 'No' : words(String(choice))}</option>)}
      </select>
    } else if (spec.type === 'array') {
      if (spec.items?.type === 'object') {
        const entries = (value as Values[]) ?? []
        control = <div>{entries.map((entry, index) => <fieldset key={index}>
          <legend>{words(key)} {index + 1}</legend><Fields schema={spec.items!} values={entry} onChange={(next) => update(entries.map((old, i) => i === index ? next : old))} root={root} prefix={`${name}.${index}.`} errors={errors} />
          <button type="button" onClick={() => update(entries.filter((_, i) => i !== index))}>Remove entry {index + 1}</button>
        </fieldset>)}<button type="button" onClick={() => update([...entries, {}])}>Add {words(key)} entry</button></div>
      } else control = <textarea {...props} value={((value as unknown[]) ?? []).join('\n')} placeholder="One reference per line" onChange={(e) => update(e.target.value.split('\n'))} onBlur={() => update(((value as string[]) ?? []).map((s) => s.trim()).filter(Boolean).map((s) => spec.items?.type === 'integer' ? Number(s) : s))} />
    } else if (spec.type === 'integer' || spec.type === 'number') {
      control = <input {...props} type="number" min={spec.minimum} max={spec.maximum} step={spec.type === 'integer' ? 1 : 'any'} value={value === undefined ? '' : String(value)} onChange={(e) => update(e.target.value === '' ? undefined : Number(e.target.value))} />
    } else if (spec.format === 'date') {
      control = <input {...props} type="date" value={String(value ?? '')} onChange={(e) => update(e.target.value)} />
    } else {
      const shared = { ...props, minLength: spec.minLength, maxLength: spec.maxLength, value: String(value ?? ''), onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => update(e.target.value) }
      control = /note|reason|description|content|statement|terms|rationale|summary|plan|basis|criteria|action|measure|outcome|scope|requirement|source|justification/.test(key) ? <textarea {...shared} rows={3} /> : <input {...shared} type="text" />
    }
    return <div className="workflow-field" key={key}><label htmlFor={inputId}>{label}{required ? ' *' : ''}</label>{control}
      {error && <p id={`${inputId}-error`} className="field-error" role="alert">{error}</p>}
    </div>
  })}</div>
}

function Form({ contract, onSaved }: { contract: Contract; onSaved: () => void }) {
  const [values, setValues] = useState<Values>({})
  const [parameters, setParameters] = useState<Values>({})
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<unknown>()
  const pathSchema: Schema = { type: 'object', properties: Object.fromEntries(contract.parameters.map((p) => [p.name, { ...p.schema, title: words(p.name) }])), required: contract.parameters.map((p) => p.name) }
  return <form className="edit-form" onSubmit={async (event) => {
    event.preventDefault()
    setBusy(true); setErrors({}); setMessage(''); setResult(undefined)
    try {
      const path = contract.path.replace(/\{(\w+)\}/g, (_, name: string) => encodeURIComponent(String(parameters[name] ?? '')))
      const result = await api.write(contract.method, path, Object.keys(contract.body.properties ?? {}).length ? payloadFor(contract.body, values) : undefined)
      setResult(result); setMessage('Saved. The register has been refreshed.'); onSaved()
    } catch (error) {
      if (error instanceof ApiValidationError) {
        setErrors(Object.fromEntries(error.fieldErrors.map((e) => [e.field, e.message])))
        setMessage(error.message)
      } else setMessage((error as Error).message)
    } finally { setBusy(false) }
  }}>
    <p className="muted">Enter your own decisions and supporting references. Required fields are marked *. Existing records and revision numbers are available in the register and record details.</p>
    <fieldset disabled={busy} className="workflow-body">
      <Fields schema={pathSchema} values={parameters} onChange={setParameters} root={parameters} errors={errors} />
      <Fields schema={contract.body} values={values} onChange={setValues} root={values} errors={errors} />
      <button type="submit">{busy ? 'Saving…' : TITLES[contract.path]}</button>
    </fieldset>
    {message && <p role={result === undefined ? 'alert' : 'status'}>{message}</p>}
    {Object.entries(errors).length > 0 && <ul className="field-error">{Object.entries(errors).map(([field, text]) => <li key={field}>{words(field)}: {text}</li>)}</ul>}
    {result !== undefined && <details open><summary>Saved record · Sample / Portfolio Assessment</summary><RecordFields value={result} /></details>}
  </form>
}

export function WorkflowForm({ group, onSaved }: { group: string; onSaved: () => void }) {
  const choices = workflows.filter((c) => c.group === group)
  const [selected, setSelected] = useState('')
  const contract = choices.find((c) => c.path === selected)
  if (!choices.length) return null
  return <section className="edit-panel">
    <label>Record or update information
      <select value={selected} onChange={(e) => setSelected(e.target.value)}>
        <option value="">Choose an action…</option>
        {choices.map((c) => <option key={c.path} value={c.path}>{TITLES[c.path]}</option>)}
      </select>
    </label>
    {contract && <Form key={contract.path} contract={contract} onSaved={onSaved} />}
  </section>
}
