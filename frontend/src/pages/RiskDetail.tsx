import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  AiAssistant,
  AiConfidenceNote,
  AiGaps,
  AiList,
  AiSection,
  AiText,
  type AiAction,
} from '../AiAssistant'
import {
  aiApi,
  type AiControlMapping,
  type AiEnvelope,
  type AiRiskAssist,
  type AiRiskDescription,
} from '../ai'
import { api, type Score } from '../api'
import { useAuth } from '../auth'
import { ChangeHistory } from '../editing'
import { useAsync } from '../useAsync'
import { ResidualForm } from './ResidualForm'
import {
  BASIS_LABEL,
  BASIS_MEANING,
  STATUS_LABEL,
  TODO_MARKER,
  TREATMENT_LABEL,
} from '../risk-labels'

function ScoreBlock({ label, score, note }: { label: string; score: Score; note: string }) {
  return (
    <div className={`score-block band-edge-${score.band.toLowerCase()}`}>
      <h3>{label}</h3>
      <p className="score-maths">
        <span title="Likelihood">L {score.likelihood}</span>
        <span className="times">×</span>
        <span title="Impact">I {score.impact}</span>
        <span className="equals">=</span>
        <strong>{score.score}</strong>
        <span className={`band band-${score.band.toLowerCase()}`}>{score.band.toLowerCase()}</span>
      </p>
      <p className="muted">{note}</p>
    </div>
  )
}

/* --- Assistant bodies ---------------------------------------------------------
 *
 * One renderer per task. Each reads only from the validated response, so a field the
 * model invented never reaches the page: the backend dropped it before it got here.
 */

function RiskAssistBody({ data }: { data: AiRiskAssist }) {
  const s = data.suggestion
  return (
    <>
      <AiText heading="In short" value={s.summary} />
      <AiList heading="Threat scenarios to consider" items={s.threat_scenarios} />
      <AiList heading="Vulnerabilities that would make them likelier" items={s.vulnerabilities} />
      <AiList heading="Control areas worth looking at" items={s.control_areas} />
      <AiList heading="Questions to investigate" items={s.questions_to_investigate} />
      <AiList heading="Treatment options that exist in principle" items={s.treatment_options} />
      <AiList heading="Observations" items={s.observations} />
      <AiGaps items={s.missing_information} />
      <AiConfidenceNote confidence={s.confidence} />
    </>
  )
}

function RiskDescriptionBody({ data }: { data: AiRiskDescription }) {
  const s = data.suggestion
  return (
    <>
      <AiSection heading="Threat, vulnerability, event, impact">
        <dl className="ai-chain">
          <dt>Threat</dt>
          <dd>{s.threat || 'Not stated'}</dd>
          <dt>Vulnerability</dt>
          <dd>{s.vulnerability || 'Not stated'}</dd>
          <dt>Event</dt>
          <dd>{s.event || 'Not stated'}</dd>
          <dt>Impact</dt>
          <dd>{s.impact || 'Not stated'}</dd>
        </dl>
      </AiSection>
      <AiText heading="Drafted statement" value={s.risk_statement} />
      <p className="muted">
        Nothing above has been saved. Putting it in the register is a separate,
        deliberate act through the endpoints that validate it.
      </p>
      <AiGaps items={s.missing_information} />
    </>
  )
}

function ControlMappingBody({ data }: { data: AiControlMapping }) {
  return (
    <>
      <AiText heading="In short" value={data.suggestion.summary} />

      <AiSection heading="Annex A controls to consider">
        {data.resolved_controls.length === 0 ? (
          <p className="muted">
            Nothing survived the catalogue check. Every identifier the model produced was
            outside ISO/IEC 27001:2022 Annex A.
          </p>
        ) : (
          <ul className="ai-list ai-controls">
            {data.resolved_controls.map((control) => (
              <li key={control.control_ref}>
                <div className="chain-row">
                  <code className="chain-ref">{control.control_ref}</code>
                  <span>{control.title}</span>
                  {control.already_linked && (
                    <span className="tag tag-ok">already linked to this risk</span>
                  )}
                  {control.soa_applicable === false && (
                    <span className="tag tag-warn">excluded in the SoA</span>
                  )}
                </div>
                <p>{control.reason}</p>
                {control.soa_implementation_status && (
                  <p className="muted">
                    Statement of Applicability:{' '}
                    {control.soa_applicable ? 'applicable' : 'excluded'},{' '}
                    {control.soa_implementation_status.replace(/_/g, ' ').toLowerCase()}.
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </AiSection>

      {data.rejected_controls.length > 0 && (
        <div className="banner banner-warn" role="note">
          <strong>
            {data.rejected_controls.length} suggested identifier
            {data.rejected_controls.length === 1 ? ' was' : 's were'} dropped.
          </strong>
          <ul>
            {data.rejected_controls.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="muted">
        A suggestion is not an applicability decision. Marking a control applicable, with
        a justification that survives the SoA rules, stays with the analyst.
      </p>
      <AiGaps items={data.suggestion.missing_information} />
    </>
  )
}

export function RiskDetail() {
  const { riskRef = '' } = useParams()
  const { session } = useAuth()
  // Bumped after a successful write so the page re-reads the record the API now holds,
  // rather than trusting the response alone: the appetite comparison and the banners
  // are derived server-side.
  const [version, setVersion] = useState(0)
  const { data: risk, error, loading } = useAsync(() => api.risk(riskRef), [riskRef, version])

  if (loading) return <p className="empty">Loading risk…</p>
  if (error) return <p className="error">Could not load {riskRef}: {error}</p>
  if (!risk) return null

  const riskActions: AiAction[] = [
    {
      key: 'summarise',
      label: 'Summarise and challenge',
      hint: 'Threat scenarios, vulnerabilities, and the questions an auditor would ask',
      run: (question) => aiApi.riskAssist(riskRef, question),
      render: (data: AiEnvelope) => <RiskAssistBody data={data as AiRiskAssist} />,
    },
    {
      key: 'statement',
      label: 'Draft the risk statement',
      hint: 'Threat, vulnerability, event and impact, in the house structure',
      run: (question) => aiApi.riskDescription({ risk_ref: riskRef, question }),
      render: (data: AiEnvelope) => <RiskDescriptionBody data={data as AiRiskDescription} />,
    },
    {
      key: 'controls',
      label: 'Suggest Annex A controls',
      hint: 'Chosen from the real 93-control catalogue, then checked back against it',
      run: (question) => aiApi.controlMapping(riskRef, question),
      render: (data: AiEnvelope) => <ControlMappingBody data={data as AiControlMapping} />,
    },
  ]

  const uncredited = risk.controls.filter((control) => !control.credits_reduction)
  const justificationOutstanding = risk.residual_justification.includes(TODO_MARKER)
  const dimensionsMoved = [
    risk.inherent.likelihood !== risk.residual.likelihood ? 'likelihood' : null,
    risk.inherent.impact !== risk.residual.impact ? 'impact' : null,
  ].filter(Boolean)

  return (
    <section className="risk-detail">
      <p className="crumb">
        <Link to="/risks">← Risk register</Link>
      </p>

      <h1>
        <span className="risk-ref">{risk.risk_ref}</span> {risk.title}
      </h1>
      <p className="card-meta">
        {risk.category_label} · owned by {risk.owner_role} · {STATUS_LABEL[risk.status]} ·
        identified {risk.date_identified} · next review {risk.next_review ?? 'not set'}
      </p>
      <p>{risk.description}</p>

      {uncredited.length > 0 && (
        <div className="banner banner-warn" role="alert">
          <strong>
            {uncredited.length} linked control{uncredited.length > 1 ? 's' : ''} may not be
            credited with any residual reduction.
          </strong>{' '}
          {uncredited.map((control) => control.control_id).join(', ')} —{' '}
          {uncredited.every((control) => control.effectiveness_basis === 'NOT_TESTED')
            ? 'never tested, so the control is an intention rather than evidence.'
            : 'untested or tested ineffective.'}{' '}
          {uncredited.length === risk.controls.length
            ? 'No control on this risk may be credited, so residual cannot be scored below inherent.'
            : 'Any reduction claimed below must be attributable to the remaining controls.'}
        </div>
      )}

      {justificationOutstanding && (
        <div className="banner banner-todo" role="note">
          <strong>Residual justification not yet written.</strong> This field is reserved for
          the author and is not machine-generated.
        </div>
      )}

      {/* The calculation, rendered as a chain rather than a result. */}
      <div className="chain">
        <ScoreBlock
          label="1. Inherent risk"
          score={risk.inherent}
          note="Before any control is considered."
        />

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <div className="score-block">
          <h3>2. Controls applied</h3>
          <ul className="control-list">
            {risk.controls.map((control) => (
              <li key={control.control_id} className={control.credits_reduction ? '' : 'uncredited'}>
                <div className="control-head">
                  <code>{control.control_id}</code>
                  <span className={`basis basis-${control.effectiveness_basis.toLowerCase()}`}>
                    {BASIS_LABEL[control.effectiveness_basis]}
                  </span>
                  {!control.credits_reduction && <span className="tag tag-warn">no credit</span>}
                </div>
                <p>{control.title}</p>
                <p className="muted">{BASIS_MEANING[control.effectiveness_basis]}</p>
                <p className="muted">
                  Annex A: {control.annex_a_refs.join(', ')} · owned by {control.owner_role}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <ScoreBlock
          label="3. Residual risk"
          score={risk.residual}
          note={
            dimensionsMoved.length === 0
              ? 'No reduction claimed — residual equals inherent.'
              : dimensionsMoved.length === 2
                ? 'Scored directly by the analyst. Both likelihood and impact moved.'
                : `Scored directly by the analyst. ${dimensionsMoved[0] === 'likelihood' ? 'Likelihood' : 'Impact'} moved; ${dimensionsMoved[0] === 'likelihood' ? 'impact' : 'likelihood'} did not.`
          }
        />

        <div className="justification">
          <h4>Residual justification</h4>
          <p className={justificationOutstanding ? 'todo-text' : ''}>
            {risk.residual_justification}
          </p>
        </div>

        {session?.canWrite && (
          <ResidualForm
            key={`${risk.risk_ref}-${version}`}
            risk={risk}
            onSaved={() => setVersion((v) => v + 1)}
          />
        )}

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <div
          className={`score-block appetite-block ${
            risk.appetite.exceeds_appetite ? 'is-breach' : 'is-within'
          }`}
        >
          <h3>4. Appetite comparison</h3>
          {risk.appetite.max_acceptable_band === null ? (
            <p>
              No appetite is defined for {risk.category_label}. This is an unanswered governance
              question, not an implicit acceptance.
            </p>
          ) : (
            <p className="score-maths">
              residual{' '}
              <span className={`band band-${risk.residual.band.toLowerCase()}`}>
                {risk.residual.band.toLowerCase()}
              </span>
              <span className="equals">vs</span>
              ceiling{' '}
              <span className={`band band-${risk.appetite.max_acceptable_band.toLowerCase()}`}>
                {risk.appetite.max_acceptable_band.toLowerCase()}
              </span>
              <span className={`tag ${risk.appetite.exceeds_appetite ? 'tag-breach' : 'tag-ok'}`}>
                {risk.appetite.exceeds_appetite ? 'above appetite' : 'within appetite'}
              </span>
            </p>
          )}
          {risk.appetite.approver_role && (
            <p className="muted">
              Appetite for {risk.category_label} is set and accepted by the{' '}
              {risk.appetite.approver_role}. Risk acceptance is a business decision, not a
              security decision.
            </p>
          )}
        </div>

        <div className="chain-arrow" aria-hidden="true">
          ↓
        </div>

        <div className="score-block">
          <h3>5. Treatment decision</h3>
          <p className="treatment-decision">{TREATMENT_LABEL[risk.treatment_decision]}</p>
          <p>{risk.treatment_summary}</p>
        </div>
      </div>

      <div className="analysis-grid">
        <div>
          <h4>Asset</h4>
          <p>{risk.asset}</p>
        </div>
        <div>
          <h4>Threat</h4>
          <p>{risk.threat}</p>
        </div>
        <div>
          <h4>Vulnerability</h4>
          <p>{risk.vulnerability}</p>
        </div>
      </div>

      <ChangeHistory recordRef={risk.risk_ref} version={version} />

      <AiAssistant
        title="AI risk assistant"
        lede="Runs against a model on this machine. It reads this risk, its linked
              controls and the appetite for its category, and returns text. It cannot
              change a score, a justification, a treatment decision or an appetite."
        actions={riskActions}
      />
    </section>
  )
}
