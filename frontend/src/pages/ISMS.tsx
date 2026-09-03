import { useState } from 'react'

import { AiAssistant, AiGaps, AiList, AiSection, AiText, type AiAction } from '../AiAssistant'
import { aiApi, type AiEnvelope, type AiPolicyDraft, type PolicyDocumentType } from '../ai'
import { api, openReport } from '../api'
import { useAsync } from '../useAsync'

type Tab = 'audits' | 'reviews' | 'nonconformities'

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="record-field">
      <h4>{label}</h4>
      <p>{value ?? '—'}</p>
    </div>
  )
}

const DOCUMENT_TYPES: { value: PolicyDocumentType; label: string }[] = [
  { value: 'POLICY', label: 'Policy' },
  { value: 'PROCEDURE', label: 'Procedure' },
  { value: 'CONTROL_DESCRIPTION', label: 'Control description' },
  { value: 'EVIDENCE_REQUEST', label: 'Evidence request' },
  { value: 'COMPLIANCE_QUESTIONNAIRE', label: 'Compliance questionnaire' },
]

function PolicyDraftBody({ data }: { data: AiPolicyDraft }) {
  const s = data.suggestion
  return (
    <>
      <AiText heading="Working title" value={s.document_title} />
      <AiText heading="Purpose" value={s.purpose} />
      <AiText heading="Scope" value={s.scope} />
      {s.sections.length > 0 && (
        <AiSection heading="Sections">
          {s.sections.map((section, index) => (
            <div key={index} className="ai-doc-section">
              <h5>{section.heading}</h5>
              <p>{section.body}</p>
            </div>
          ))}
        </AiSection>
      )}
      <AiList heading="Open questions the organisation has to answer" items={s.open_questions} />
      <p className="muted">
        A draft, and only a draft. Mentioning ISO 27001 does not make a document
        compliant with it; that is determined by an assessment, and by an assessor.
      </p>
      <AiGaps items={s.missing_information} />
    </>
  )
}

/** Drafting sits on the ISMS records page because that is where the documented
 *  information lives. The assistant writes against FinFlow's actual shape, taken from
 *  the recorded scope: fully remote, no premises, one cloud region, a third-party
 *  payment processor. The failure mode of a generic draft is a policy controlling
 *  physical access to data centres for a company that has none. */
function DraftingAssistant() {
  const [documentType, setDocumentType] = useState<PolicyDocumentType>('POLICY')
  const [topic, setTopic] = useState('')
  const [refs, setRefs] = useState('')

  const actions: AiAction[] = [
    {
      key: 'draft',
      label: 'Draft it',
      hint: 'Written for FinFlow as scoped, not for a generic company',
      run: (question) =>
        aiApi.policyDraft({
          document_type: documentType,
          topic: topic.trim(),
          annex_a_refs: refs
            .split(',')
            .map((ref) => ref.trim())
            .filter(Boolean)
            .slice(0, 10),
          question,
        }),
      render: (result: AiEnvelope) => <PolicyDraftBody data={result as AiPolicyDraft} />,
    },
  ]

  return (
    <AiAssistant
      title="AI drafting assistant"
      lede="Policies, procedures, control descriptions, evidence requests and
            questionnaires. Drafts only, for a person to edit and own."
      actions={actions}
      extras={
        <div className="ai-fields">
          <label>
            <span className="muted">Document type</span>
            <select
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value as PolicyDocumentType)}
            >
              {DOCUMENT_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="muted">Topic</span>
            <input
              type="text"
              value={topic}
              maxLength={200}
              placeholder="e.g. privileged access to production"
              onChange={(event) => setTopic(event.target.value)}
            />
          </label>
          <label>
            <span className="muted">Annex A controls it supports, comma separated</span>
            <input
              type="text"
              value={refs}
              placeholder="e.g. A.5.15, A.8.5"
              onChange={(event) => setRefs(event.target.value)}
            />
          </label>
        </div>
      }
    />
  )
}

export function ISMS() {
  const audits = useAsync(() => api.internalAudits(), [])
  const reviews = useAsync(() => api.managementReviews(), [])
  const ncs = useAsync(() => api.nonconformities(), [])
  const [tab, setTab] = useState<Tab>('audits')

  return (
    <section>
      <h1>ISMS records</h1>
      <p className="lede">
        The clause-level records a certification auditor asks for: the internal audit
        programme (9.2), management review (9.3), and nonconformity and corrective action
        (10.2). Deliberately plain — these exist to be read, not navigated.
      </p>

      <div className="framework-switch">
        {(['audits', 'reviews', 'nonconformities'] as Tab[]).map((option) => (
          <button
            key={option}
            type="button"
            className={option === tab ? 'active' : ''}
            onClick={() => setTab(option)}
          >
            {option === 'audits'
              ? 'Clause 9.2 — Internal audit'
              : option === 'reviews'
                ? 'Clause 9.3 — Management review'
                : 'Clause 10.2 — Nonconformity'}
          </button>
        ))}
        <button
          type="button"
          className="pdf-link"
          onClick={() => openReport(api.ismsRecordsUrl())}
        >
          Records export PDF →
        </button>
      </div>

      {tab === 'audits' &&
        (audits.data ?? []).map((audit) => (
          <article key={audit.audit_ref} className="record">
            <h2>
              <code>{audit.audit_ref}</code> {audit.title}
            </h2>
            <p className="card-meta">
              {audit.status.replace('_', ' ').toLowerCase()} · planned {audit.planned_start} to{' '}
              {audit.planned_end}
              {audit.actual_start &&
                ` · actual ${audit.actual_start} to ${audit.actual_end ?? 'ongoing'}`}
            </p>
            <div className="record-grid">
              <Field label="Scope" value={audit.scope} />
              <Field label="Objectives" value={audit.objectives} />
              <Field label="Audit criteria" value={audit.criteria} />
              <Field label="Auditor" value={audit.auditor} />
            </div>
            <Field label="Independence (Clause 9.2.2 c)" value={audit.independence_note} />
            {audit.outcome_summary && <Field label="Outcome" value={audit.outcome_summary} />}
          </article>
        ))}

      {tab === 'reviews' &&
        (reviews.data ?? []).map((review) => (
          <article key={review.review_ref} className="record">
            <h2>
              <code>{review.review_ref}</code> {review.review_date}
            </h2>
            <p className="card-meta">
              Chaired by {review.chair} · next review {review.next_review_date ?? 'not set'}
            </p>
            <Field label="Attendees" value={review.attendees} />
            <div className="record-pre">
              <h4>Inputs considered (Clause 9.3.2)</h4>
              <pre>{review.inputs_considered}</pre>
            </div>
            <Field label="Decisions" value={review.decisions} />
            <div className="record-pre">
              <h4>Actions</h4>
              <pre>{review.actions}</pre>
            </div>
          </article>
        ))}

      {tab === 'nonconformities' && (
        <>
          <div className="banner banner-warn" role="note">
            <strong>Correction is not corrective action.</strong> A correction fixes the
            instance; corrective action eliminates the cause so it does not recur. Clause 10.2
            requires both, plus a review of whether the action worked — which is why a
            nonconformity cannot be closed here without an effectiveness check result.
          </div>
          {(ncs.data ?? []).map((nc) => (
            <article key={nc.nc_ref} className="record">
              <h2>
                <code>{nc.nc_ref}</code>{' '}
                <span className="muted">{nc.status.replace(/_/g, ' ').toLowerCase()}</span>
              </h2>
              <p className="card-meta">
                Identified {nc.identified_date} by {nc.identified_by} · owner {nc.owner}
                {nc.finding_ref && ` · from ${nc.finding_ref}`}
              </p>
              <Field label="Description" value={nc.description} />
              <Field label="Correction (immediate)" value={nc.immediate_correction} />
              <Field label="Root cause analysis" value={nc.root_cause_analysis} />
              <Field
                label="Corrective action (eliminates the cause)"
                value={nc.corrective_action}
              />
              <div className="record-grid">
                <Field label="Target date" value={nc.target_date} />
                <Field label="Effectiveness check due" value={nc.effectiveness_check_date} />
                <Field label="Closed" value={nc.closure_date} />
              </div>
              {nc.effectiveness_check_result && (
                <Field label="Effectiveness check result" value={nc.effectiveness_check_result} />
              )}
            </article>
          ))}
        </>
      )}
      <DraftingAssistant />
    </section>
  )
}
