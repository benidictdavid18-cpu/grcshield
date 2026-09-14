import { useState } from 'react'

import { api, type ImplementationStatus, type SoADetail } from '../api'
import { FieldError, UnplacedErrors, useSubmit } from '../editing'
import { IMPLEMENTATION_LABEL } from '../risk-labels'

const STATUSES: ImplementationStatus[] = ['NOT_IMPLEMENTED', 'PARTIALLY_IMPLEMENTED', 'IMPLEMENTED']
const FIELDS = [
  'applicable',
  'justification_inclusion',
  'justification_exclusion',
  'implementation_status',
  'implementation_description',
  'owner',
]

/** Edit a Statement of Applicability entry.
 *
 *  Three rules can refuse the submission, all on the server (Clause 6.1.3 d):
 *  applicable needs an inclusion justification that cites a driver -- "required by
 *  ISO 27001" is circular and is rejected by name; excluded needs an exclusion
 *  justification and is forced to NOT_IMPLEMENTED; and applicable-but-not-implemented
 *  is a gap, which needs a live remediation item. The last one is refused on a field
 *  this form does not edit (`linked_remediation_ids`), which is exactly the case
 *  `UnplacedErrors` exists for. */
export function SoAEditForm({
  entry,
  onSaved,
}: {
  entry: SoADetail
  onSaved: (e: SoADetail) => void
}) {
  const [open, setOpen] = useState(false)
  const [applicable, setApplicable] = useState(entry.applicable)
  const [status, setStatus] = useState<ImplementationStatus>(entry.implementation_status)
  const [inclusion, setInclusion] = useState(entry.justification_inclusion ?? '')
  const [exclusion, setExclusion] = useState(entry.justification_exclusion ?? '')
  const [description, setDescription] = useState(entry.implementation_description ?? '')
  const [owner, setOwner] = useState(entry.owner)

  const { state, submit, reset } = useSubmit(
    () =>
      api.updateSoAEntry(entry.control_ref, {
        applicable,
        implementation_status: applicable ? status : 'NOT_IMPLEMENTED',
        // Empty is null on the record; sending '' would register as a change.
        justification_inclusion: inclusion.trim() || null,
        justification_exclusion: exclusion.trim() || null,
        implementation_description: description.trim() || null,
        owner,
      }),
    (updated) => {
      onSaved(updated)
      setOpen(false)
    },
  )

  return (
    <section className={`edit-panel ${open ? 'is-open' : ''}`}>
      <button
        type="button"
        className="ai-toggle"
        onClick={() => {
          setOpen(!open)
          reset()
        }}
        aria-expanded={open}
      >
        <span className="ai-toggle-mark" aria-hidden="true">
          {open ? '−' : '+'}
        </span>
        Edit this entry
        <span className="ai-toggle-hint">writes to the SoA · rule-checked</span>
      </button>

      {open && (
        <form className="edit-form" onSubmit={submit} noValidate>
          <div className="edit-fields">
            <label>
              Applicability
              <select
                name="applicable"
                value={applicable ? 'yes' : 'no'}
                onChange={(e) => setApplicable(e.target.value === 'yes')}
              >
                <option value="yes">Applicable</option>
                <option value="no">Excluded</option>
              </select>
              <FieldError refusal={state.refusal} field="applicable" />
            </label>
            <label>
              Implementation status
              <select
                name="implementation_status"
                value={applicable ? status : 'NOT_IMPLEMENTED'}
                disabled={!applicable}
                onChange={(e) => setStatus(e.target.value as ImplementationStatus)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {IMPLEMENTATION_LABEL[s]}
                  </option>
                ))}
              </select>
              <FieldError refusal={state.refusal} field="implementation_status" />
            </label>
            <label>
              Owner
              <input name="owner" value={owner} onChange={(e) => setOwner(e.target.value)} />
              <FieldError refusal={state.refusal} field="owner" />
            </label>
          </div>

          {applicable ? (
            <label className="edit-wide">
              Inclusion justification
              <textarea
                name="justification_inclusion"
                rows={3}
                value={inclusion}
                onChange={(e) => setInclusion(e.target.value)}
                placeholder="Which risk, or which legal, regulatory or contractual obligation, drives this control."
              />
              <FieldError refusal={state.refusal} field="justification_inclusion" />
            </label>
          ) : (
            <label className="edit-wide">
              Exclusion justification
              <textarea
                name="justification_exclusion"
                rows={3}
                value={exclusion}
                onChange={(e) => setExclusion(e.target.value)}
                placeholder="Where the risk went: transferred to whom, or redirected to which control."
              />
              <FieldError refusal={state.refusal} field="justification_exclusion" />
            </label>
          )}

          <label className="edit-wide">
            Implementation description
            <textarea
              name="implementation_description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <FieldError refusal={state.refusal} field="implementation_description" />
          </label>

          <UnplacedErrors refusal={state.refusal} shown={FIELDS} />
          {state.message && (
            <div className="banner banner-warn" role="alert">
              {state.message}
            </div>
          )}

          <div className="edit-actions">
            <button type="submit" className="primary" disabled={state.busy}>
              {state.busy ? 'Saving…' : 'Save entry'}
            </button>
            <button type="button" onClick={() => setOpen(false)} disabled={state.busy}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
