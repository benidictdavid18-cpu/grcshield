import { useState } from 'react'

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
    </section>
  )
}
