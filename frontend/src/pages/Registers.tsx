import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'
import { useAsync } from '../useAsync'

type Tab = 'acceptance' | 'ropa' | 'dpia' | 'continuity' | 'assets'

const LAWFUL_BASIS_LABEL: Record<string, string> = {
  CONSENT: 'Consent — Art. 6(1)(a)',
  CONTRACT: 'Contract — Art. 6(1)(b)',
  LEGAL_OBLIGATION: 'Legal obligation — Art. 6(1)(c)',
  VITAL_INTERESTS: 'Vital interests — Art. 6(1)(d)',
  PUBLIC_TASK: 'Public task — Art. 6(1)(e)',
  LEGITIMATE_INTERESTS: 'Legitimate interests — Art. 6(1)(f)',
}

const SAFEGUARD_LABEL: Record<string, string> = {
  NOT_APPLICABLE: 'No transfer',
  ADEQUACY_DECISION: 'Adequacy decision',
  STANDARD_CONTRACTUAL_CLAUSES: 'Standard Contractual Clauses',
  BINDING_CORPORATE_RULES: 'Binding Corporate Rules',
  DEROGATION: 'Art. 49 derogation',
}

const OUTCOME_LABEL: Record<string, string> = {
  PROCEED: 'Proceed',
  PROCEED_WITH_MEASURES: 'Proceed with measures',
  CONSULT_SUPERVISORY_AUTHORITY: 'Consult supervisory authority',
  DO_NOT_PROCEED: 'Do not proceed',
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="record-field">
      <h4>{label}</h4>
      <p>{value ?? '—'}</p>
    </div>
  )
}

function RiskChips({ risks }: { risks: { risk_ref: string; residual_band: string; exceeds_appetite: boolean | null }[] }) {
  if (risks.length === 0) return <span className="muted">none linked</span>
  return (
    <>
      {risks.map((risk) => (
        <Link key={risk.risk_ref} to={`/risks/${risk.risk_ref}`} className="chain-ref chip">
          {risk.risk_ref}
          <span className={`band band-${risk.residual_band.toLowerCase()}`}>
            {risk.residual_band.toLowerCase()}
          </span>
        </Link>
      ))}
    </>
  )
}

function Acceptance() {
  const exceptions = useAsync(() => api.riskExceptions(), [])
  const summary = useAsync(() => api.exceptionSummary(), [])

  return (
    <>
      <div className="banner banner-warn" role="note">
        <strong>Risk acceptance is a business decision, not a security decision.</strong>{' '}
        Security advises on the risk; the person who answers for the consequence decides to
        carry it. Every approver below is the owner of the linked risk or the Chief Executive
        Officer — the API rejects an acceptance signed by the security function. Every
        acceptance expires, because one without an end date is a permanent decision disguised
        as a temporary one.
      </div>

      {summary.data && (
        <>
          <div className="tiles">
            <div className="tile">
              <span className="tile-value">{summary.data.live}</span>
              <span className="tile-label">live acceptances</span>
            </div>
            <div className={`tile ${summary.data.expiring_soon > 0 ? 'tile-todo' : ''}`}>
              <span className="tile-value">{summary.data.expiring_soon}</span>
              <span className="tile-label">
                expiring within {summary.data.expiry_warning_days} days
              </span>
            </div>
            <div className={`tile ${summary.data.expired > 0 ? 'tile-alert' : ''}`}>
              <span className="tile-value">{summary.data.expired}</span>
              <span className="tile-label">expired</span>
            </div>
            <div className={`tile ${summary.data.uncovered_breaches.length > 0 ? 'tile-alert' : ''}`}>
              <span className="tile-value">{summary.data.uncovered_breaches.length}</span>
              <span className="tile-label">above appetite, no live acceptance</span>
            </div>
          </div>

          {summary.data.uncovered_breaches.length > 0 && (
            <div className="banner banner-warn" role="alert">
              <strong>
                {summary.data.uncovered_breaches.length} risks sit above their category
                appetite with no live acceptance covering them:
              </strong>{' '}
              {summary.data.uncovered_breaches.join(', ')}. An exposure carried without a
              decision is worse than a documented acceptance — nobody has agreed to it.
            </div>
          )}
        </>
      )}

      {(exceptions.data ?? []).map((exception) => (
        <article key={exception.exception_ref} className="record">
          <h2>
            <code>{exception.exception_ref}</code>{' '}
            <span className={`exc exc-${exception.state.toLowerCase()}`}>
              {exception.state.replace(/_/g, ' ').toLowerCase()}
            </span>
          </h2>
          <p className="card-meta">
            <Link to={`/risks/${exception.risk_ref}`} className="chain-ref">
              {exception.risk_ref}
            </Link>{' '}
            {exception.risk_title} · residual{' '}
            <span className={`band band-${exception.residual_band.toLowerCase()}`}>
              {exception.residual_band.toLowerCase()}
            </span>
            {exception.exceeds_appetite && <span className="tag tag-breach">above appetite</span>}
          </p>

          <div className="record-grid">
            <Field label="Requested by" value={exception.requested_by} />
            <Field
              label="Approved by"
              value={
                <>
                  {exception.approver_role}
                  {exception.approver_role === exception.risk_owner_role ? (
                    <span className="tag tag-ok">risk owner</span>
                  ) : (
                    <span className="tag tag-warn">escalated</span>
                  )}
                </>
              }
            />
            <Field label="Approved" value={exception.approval_date ?? 'not approved'} />
            <Field
              label="Expires"
              value={
                <>
                  {exception.expiry_date}
                  <span className="muted">
                    {' '}
                    ({exception.days_remaining < 0
                      ? `${Math.abs(exception.days_remaining)} days ago`
                      : `in ${exception.days_remaining} days`})
                  </span>
                </>
              }
            />
          </div>

          <Field label="Business justification" value={exception.business_justification} />
          <Field label="Compensating controls" value={exception.compensating_controls} />
          <Field label="Review trigger" value={exception.review_trigger} />
          {exception.decision_note && (
            <Field label="Decision note" value={exception.decision_note} />
          )}
        </article>
      ))}
    </>
  )
}

function Ropa() {
  const entries = useAsync(() => api.ropa(), [])

  return (
    <>
      <p className="lede">
        GDPR Article 30 — Record of Processing Activities. A transfer outside the EEA cannot
        be recorded without a Chapter V safeguard, and a lawful basis of legitimate interests
        cannot be recorded without the balancing test. Both are rejected at the API.
      </p>

      {(entries.data ?? []).map((entry) => (
        <article key={entry.ropa_ref} className="record">
          <h2>
            <code>{entry.ropa_ref}</code> {entry.processing_activity}
          </h2>
          <p className="card-meta">
            {LAWFUL_BASIS_LABEL[entry.lawful_basis]} · owned by {entry.owner_role}
            {entry.transfers_outside_eea && (
              <span className="tag tag-warn">third-country transfer</span>
            )}
            {entry.dpia_refs.map((ref) => (
              <span key={ref} className="tag tag-ok">
                {ref}
              </span>
            ))}
          </p>

          <Field label="Purpose" value={entry.purpose} />
          {entry.legitimate_interests_assessment && (
            <Field
              label="Legitimate interests balancing test"
              value={entry.legitimate_interests_assessment}
            />
          )}
          <div className="record-grid">
            <Field label="Data subjects" value={entry.data_subject_categories} />
            <Field label="Personal data" value={entry.personal_data_categories} />
            <Field label="Recipients" value={entry.recipients} />
            <Field label="Retention" value={entry.retention_period} />
          </div>
          {entry.transfers_outside_eea && (
            <div className="record-grid">
              <Field label="Transfer safeguard" value={SAFEGUARD_LABEL[entry.transfer_safeguard]} />
              <Field label="Transfer detail" value={entry.transfer_detail} />
            </div>
          )}
          <Field label="Security measures" value={entry.security_measures_summary} />

          <div className="record-grid">
            <Field
              label="Assets"
              value={
                entry.assets.length > 0 ? (
                  entry.assets.map((asset) => (
                    <code key={asset.asset_ref} className="chip">
                      {asset.asset_ref}
                    </code>
                  ))
                ) : (
                  <span className="muted">none linked</span>
                )
              }
            />
            <Field label="Risks" value={<RiskChips risks={entry.risks} />} />
            <Field
              label="Controls (Art. 30(1)(g))"
              value={entry.controls.map((control) => (
                <code
                  key={control.control_id}
                  className={`chip ${control.credited ? '' : 'chip-bad'}`}
                  title={
                    control.credited
                      ? control.operating_effectiveness
                      : `${control.control_id} is currently rated ${control.operating_effectiveness} — this record claims a measure that is not working`
                  }
                >
                  {control.control_id}
                </code>
              ))}
            />
          </div>
        </article>
      ))}
    </>
  )
}

function Dpias() {
  const dpias = useAsync(() => api.dpias(), [])
  const overview = useAsync(() => api.privacyOverview(), [])

  return (
    <>
      <p className="lede">
        GDPR Article 35 — Data Protection Impact Assessments. Where residual risk remains
        high after mitigation, Article 36(1) requires prior consultation with the supervisory
        authority: the controller cannot decide alone to proceed. That dependency is enforced,
        not documented.
      </p>

      {overview.data && (
        <div className="tiles">
          <div className="tile">
            <span className="tile-value">{overview.data.dpias}</span>
            <span className="tile-label">assessments</span>
          </div>
          <div className={`tile ${overview.data.dpias_high_residual > 0 ? 'tile-alert' : ''}`}>
            <span className="tile-value">{overview.data.dpias_high_residual}</span>
            <span className="tile-label">high residual risk</span>
          </div>
          <div
            className={`tile ${overview.data.dpias_awaiting_supervisory_consultation > 0 ? 'tile-alert' : ''}`}
          >
            <span className="tile-value">
              {overview.data.dpias_awaiting_supervisory_consultation}
            </span>
            <span className="tile-label">awaiting Art. 36 consultation</span>
          </div>
          <div className={`tile ${overview.data.dpias_review_overdue > 0 ? 'tile-todo' : ''}`}>
            <span className="tile-value">{overview.data.dpias_review_overdue}</span>
            <span className="tile-label">review overdue</span>
          </div>
        </div>
      )}

      {(dpias.data ?? []).map((dpia) => (
        <article key={dpia.dpia_ref} className="record">
          <h2>
            <code>{dpia.dpia_ref}</code> {dpia.title}
          </h2>
          <p className="card-meta">
            {OUTCOME_LABEL[dpia.outcome]} · residual{' '}
            <span className={`band band-${dpia.residual_risk.toLowerCase()}`}>
              {dpia.residual_risk.toLowerCase()}
            </span>{' '}
            · assessed {dpia.assessment_date} by {dpia.assessed_by}
            {dpia.ropa_ref && <span className="tag tag-ok">{dpia.ropa_ref}</span>}
            {dpia.review_overdue && <span className="tag tag-breach">review overdue</span>}
          </p>

          {dpia.residual_risk === 'HIGH' && !dpia.supervisory_authority_consulted && (
            <div className="banner banner-warn" role="alert">
              <strong>Article 36(1) consultation outstanding.</strong> Residual risk is high
              after mitigation, so processing cannot continue on the controller's own
              assessment until the supervisory authority has been consulted.
            </div>
          )}

          <Field label="Why a DPIA was required" value={dpia.trigger_reason} />
          <Field label="Processing" value={dpia.processing_description} />
          <Field label="Necessity and proportionality" value={dpia.necessity_and_proportionality} />
          <Field label="Risks to data subjects" value={dpia.risks_to_data_subjects} />
          <Field label="Mitigating measures" value={dpia.mitigating_measures} />
          <Field label="Residual risk" value={dpia.residual_risk_note} />
          <div className="record-grid">
            <Field
              label="DPO consulted (Art. 35(2))"
              value={dpia.dpo_consulted ? 'Yes' : 'No'}
            />
            <Field
              label="Supervisory authority (Art. 36)"
              value={dpia.supervisory_authority_consulted ? 'Consulted' : 'Not consulted'}
            />
            <Field label="Review date" value={dpia.review_date} />
          </div>
          {dpia.dpo_advice && <Field label="DPO advice" value={dpia.dpo_advice} />}
          <div className="record-grid">
            <Field
              label="Assets"
              value={dpia.assets.map((asset) => (
                <code key={asset.asset_ref} className="chip">
                  {asset.asset_ref}
                </code>
              ))}
            />
            <Field label="Risks" value={<RiskChips risks={dpia.risks} />} />
          </div>
        </article>
      ))}
    </>
  )
}

function Continuity() {
  const processes = useAsync(() => api.bia(), [])

  const money = (value: number, currency: string) =>
    value === 0
      ? '—'
      : new Intl.NumberFormat('en-GB', {
          style: 'currency',
          currency,
          maximumFractionDigits: 0,
        }).format(value)

  return (
    <>
      <p className="lede">
        Business impact analysis. MTPD is how long the business can survive without the
        process; RTO and RPO are what recovery is planned to achieve. An RTO beyond the MTPD
        is a plan that fails on the day it is written, so the relationship is enforced at the
        API and in the database.
      </p>

      <table className="register">
        <thead>
          <tr>
            <th>Process</th>
            <th className="num">RTO</th>
            <th className="num">RPO</th>
            <th className="num">MTPD</th>
            <th className="num">Headroom</th>
            <th className="num">1 hour</th>
            <th className="num">24 hours</th>
            <th className="num">1 week</th>
          </tr>
        </thead>
        <tbody>
          {(processes.data ?? []).map((bia) => (
            <tr key={bia.bia_ref}>
              <td>
                <code>{bia.bia_ref}</code> {bia.process_name}
                <span className="row-sub">{bia.owner_role}</span>
              </td>
              <td className="num">{bia.rto_hours}h</td>
              <td className="num">{bia.rpo_hours}h</td>
              <td className="num">{bia.mtpd_hours}h</td>
              <td className="num">{bia.recovery_headroom_hours}h</td>
              <td className="num">{money(bia.impact_1h, bia.currency)}</td>
              <td className="num">{money(bia.impact_24h, bia.currency)}</td>
              <td className="num">{money(bia.impact_1w, bia.currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {(processes.data ?? []).map((bia) => (
        <article key={bia.bia_ref} className="record">
          <h2>
            <code>{bia.bia_ref}</code> {bia.process_name}
          </h2>
          <p className="card-meta">
            Owned by {bia.owner_role} · reviewed {bia.last_reviewed ?? 'never'}
          </p>
          <Field label="Process" value={bia.process_description} />
          <Field label="Financial impact" value={bia.impact_note} />
          <Field label="Workaround" value={bia.workaround} />
          {bia.recovery_note && <Field label="Recovery note" value={bia.recovery_note} />}
          <div className="record-grid">
            <Field
              label="Dependent assets"
              value={bia.assets.map((asset) => (
                <code key={asset.asset_ref} className="chip" title={asset.name}>
                  {asset.asset_ref}
                </code>
              ))}
            />
            <Field
              label="Continuity controls"
              value={bia.controls.map((control) => (
                <code
                  key={control.control_id}
                  className={`chip ${control.credited ? '' : 'chip-bad'}`}
                  title={control.operating_effectiveness}
                >
                  {control.control_id}
                </code>
              ))}
            />
            <Field label="Linked risks" value={<RiskChips risks={bia.risks} />} />
          </div>
        </article>
      ))}
    </>
  )
}

function Assets() {
  const assets = useAsync(() => api.assets(), [])

  return (
    <>
      <p className="lede">
        The asset register exists because RoPA entries, DPIAs and business impact analyses
        all need something concrete to point at. "Customer data" is not an asset; the
        production cluster in eu-west-1 is.
      </p>
      <table className="register">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Type</th>
            <th>Classification</th>
            <th>Owner</th>
            <th>Location</th>
            <th>Personal data</th>
          </tr>
        </thead>
        <tbody>
          {(assets.data ?? []).map((asset) => (
            <tr key={asset.asset_ref}>
              <td>
                <code>{asset.asset_ref}</code> {asset.name}
                <span className="row-sub">{asset.description}</span>
              </td>
              <td>{asset.asset_type.replace(/_/g, ' ').toLowerCase()}</td>
              <td>
                <span className={`cls cls-${asset.classification.toLowerCase()}`}>
                  {asset.classification.toLowerCase()}
                </span>
              </td>
              <td>{asset.owner_role}</td>
              <td>{asset.hosting_location}</td>
              <td>{asset.holds_personal_data ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

export function Registers() {
  const [tab, setTab] = useState<Tab>('acceptance')

  return (
    <section>
      <h1>Registers</h1>

      <div className="framework-switch">
        {(
          [
            ['acceptance', 'Risk acceptance'],
            ['ropa', 'RoPA — Art. 30'],
            ['dpia', 'DPIA — Art. 35'],
            ['continuity', 'Business impact'],
            ['assets', 'Assets'],
          ] as [Tab, string][]
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={value === tab ? 'active' : ''}
            onClick={() => setTab(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'acceptance' && <Acceptance />}
      {tab === 'ropa' && <Ropa />}
      {tab === 'dpia' && <Dpias />}
      {tab === 'continuity' && <Continuity />}
      {tab === 'assets' && <Assets />}
    </section>
  )
}
