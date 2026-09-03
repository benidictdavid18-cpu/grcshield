import { useMemo, useState } from 'react'

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
  type AiControlTestAssist,
  type AiEnvelope,
  type AiFindingDraft,
  type AiRemediationAssist,
} from '../ai'
import { api, type ControlTestSummary } from '../api'
import { useAsync } from '../useAsync'
import {
  BASIS_LABEL,
  CONCLUSION_LABEL,
  DESIGN_LABEL,
  EFFECTIVENESS_RULE,
  OPERATING_LABEL,
  SAMPLE_METHOD_LABEL,
} from '../risk-labels'

type Tab = 'tests' | 'controls' | 'findings'

/* --- Assistant bodies ----------------------------------------------------------
 *
 * Note what is not here. No conclusion, no design or operating rating, no severity, no
 * owner, no due date. Those are not omitted from the rendering; they are absent from
 * the response schema, so there is nothing to render.
 */

function TestAssistBody({ data }: { data: AiControlTestAssist }) {
  const s = data.suggestion
  return (
    <>
      <AiText heading="In short" value={s.summary} />
      <AiText heading="What the evidence is said to show" value={s.evidence_summary} />
      <AiList heading="Possible exceptions" items={s.possible_exceptions} />
      <AiList heading="Evidence you might expect and cannot see" items={s.missing_evidence} />
      <AiList heading="Follow-up questions" items={s.follow_up_questions} />
      <AiList heading="Why an exception here might matter" items={s.why_it_might_matter} />
      <AiList heading="Further testing to consider" items={s.additional_testing} />
      <AiList heading="Observations" items={s.observations} />
      <p className="muted">
        The conclusion on this workpaper, and the control's design and operating ratings,
        stay with the tester and the reviewer. The assistant has not seen the evidence
        artifacts; it has read how they were described.
      </p>
      <AiGaps items={s.missing_information} />
      <AiConfidenceNote confidence={s.confidence} />
    </>
  )
}

function FindingDraftBody({ data }: { data: AiFindingDraft }) {
  const s = data.suggestion
  return (
    <>
      <AiText heading="Draft title" value={s.draft_title} />
      <AiText heading="Condition, what was found" value={s.condition} />
      <AiText heading="Criteria, what was expected" value={s.criteria} />
      <AiText heading="Risk and impact" value={s.risk_and_impact} />
      <AiList heading="Possible root causes, as hypotheses" items={s.possible_root_causes} />
      <AiText
        heading="Suggested remediation language"
        value={s.suggested_remediation_language}
      />
      <p className="muted">
        This is the first step of test, draft finding, human review, final finding. No
        finding has been created, no severity assigned and no status changed.
      </p>
      <AiGaps items={s.missing_information} />
    </>
  )
}

function RemediationBody({ data }: { data: AiRemediationAssist }) {
  const s = data.suggestion
  return (
    <>
      <AiSection heading="Correction and corrective action">
        <dl className="ai-chain">
          <dt>Correction, fixes this instance</dt>
          <dd>{s.correction || 'Not stated'}</dd>
          <dt>Corrective action, stops it recurring</dt>
          <dd>{s.corrective_action || 'Not stated'}</dd>
        </dl>
        <p className="muted">
          Clause 10.2 asks for both. A plan with only a correction produces the same
          finding again next year.
        </p>
      </AiSection>
      <AiList heading="Root cause questions to ask" items={s.root_cause_questions} />
      <AiList heading="Steps" items={s.remediation_steps} />
      <AiList
        heading="Evidence that would justify closing it"
        items={s.evidence_required_to_close}
      />
      {s.suggested_owner_role && (
        <AiText heading="Suggested owner role" value={s.suggested_owner_role} />
      )}
      <AiText heading="Argument for the priority" value={s.priority_rationale} />
      <p className="muted">
        A role, not a person, and no date at all. Owners and deadlines are agreed with
        the business; a date nobody agreed is not a plan.
      </p>
      <AiGaps items={s.missing_information} />
    </>
  )
}

function Workpaper({ testRef, onClose }: { testRef: string; onClose: () => void }) {
  const { data, error, loading } = useAsync(() => api.controlTest(testRef), [testRef])

  const testActions: AiAction[] = [
    {
      key: 'analyse',
      label: 'Analyse the workpaper',
      hint: 'Evidence as described, possible exceptions, follow-up questions',
      run: (question) => aiApi.controlTestAssist(testRef, question),
      render: (result: AiEnvelope) => <TestAssistBody data={result as AiControlTestAssist} />,
    },
    {
      key: 'finding',
      label: 'Draft a finding',
      hint: 'Condition, criteria, risk and impact, possible root causes',
      run: (question) => aiApi.findingDraft(testRef, question),
      render: (result: AiEnvelope) => <FindingDraftBody data={result as AiFindingDraft} />,
    },
  ]

  return (
    <aside className="drawer soa-drawer">
      <div className="drawer-head">
        <h2>{testRef}</h2>
        <button type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      {loading && <p className="empty">Loading workpaper…</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <p className="drawer-title">
            {data.control_id} — {data.control_title}
          </p>
          <p className="card-meta">
            Tested by {data.tester} on {data.test_date} · period {data.period_covered_start} to{' '}
            {data.period_covered_end}
          </p>

          <div
            className={`scope-block ${data.conclusion === 'PASS' ? 'is-in' : 'is-out'}`}
          >
            <strong>{CONCLUSION_LABEL[data.conclusion]}</strong>
            <p>
              {data.exceptions_count} exception{data.exceptions_count === 1 ? '' : 's'} in a
              sample of {data.sample_size} ({Math.round(data.exception_rate * 100)}%)
            </p>
            {data.linked_finding_ref && (
              <p className="muted">Raised {data.linked_finding_ref}.</p>
            )}
          </div>

          <h3>Objective</h3>
          <p className="muted">{data.test_objective}</p>

          <h3>Procedure</h3>
          <p className="muted">{data.test_procedure}</p>

          <h3>Population and sample</h3>
          <p className="muted">{data.population_description}</p>
          <p className="sample-line">
            <span>
              population <strong>{data.population_size}</strong>
            </span>
            <span>
              sample <strong>{data.sample_size}</strong>
            </span>
            <span className="basis basis-design_only">
              {SAMPLE_METHOD_LABEL[data.sample_selection_method]}
            </span>
          </p>
          <p className={data.rationale_outstanding ? 'todo-text' : 'muted'}>
            {data.sampling_rationale}
          </p>

          <h3>Results</h3>
          <p className="muted">{data.results_summary}</p>
          {data.exception_details && (
            <>
              <h3>Exceptions</h3>
              <p className="muted">{data.exception_details}</p>
            </>
          )}

          <h3>Evidence</h3>
          {data.evidence.length === 0 ? (
            <p className="muted">No evidence linked.</p>
          ) : (
            <ul className="chain-list">
              {data.evidence.map((item) => (
                <li key={item.evidence_ref}>
                  <div className="chain-row">
                    <code className="chain-ref">{item.evidence_ref}</code>
                    {item.expired && <span className="tag tag-warn">expired</span>}
                  </div>
                  <p>{item.title}</p>
                </li>
              ))}
            </ul>
          )}

          <h3>Review</h3>
          <p className="muted">
            {data.is_reviewed
              ? `Reviewed by ${data.reviewed_by} on ${data.review_date}. The reviewer cannot be the tester — a workpaper reviewed by its own author has not been reviewed.`
              : 'Not yet reviewed.'}
          </p>

          <AiAssistant
            title="AI test assistant"
            lede="Reads this workpaper, the control it tests and how its evidence was
                  described. It cannot record a conclusion, rate the control, or raise
                  a finding."
            actions={testActions}
          />
        </>
      )}
    </aside>
  )
}

export function Testing() {
  const overview = useAsync(() => api.testingOverview(), [])
  const tests = useAsync(() => api.controlTests(), [])
  const controls = useAsync(() => api.internalControls(), [])
  const findings = useAsync(() => api.findings(), [])
  const [tab, setTab] = useState<Tab>('tests')
  const [selected, setSelected] = useState<string | null>(null)

  const sortedTests = useMemo(
    () =>
      [...(tests.data ?? [])].sort(
        (a: ControlTestSummary, b: ControlTestSummary) =>
          ['FAIL', 'PASS_WITH_EXCEPTIONS', 'PASS'].indexOf(a.conclusion) -
            ['FAIL', 'PASS_WITH_EXCEPTIONS', 'PASS'].indexOf(b.conclusion) ||
          a.test_ref.localeCompare(b.test_ref),
      ),
    [tests.data],
  )

  const summary = overview.data

  return (
    <section className="library">
      <div className="library-main">
        <h1>Control testing</h1>
        <p className="lede">
          Design and operating effectiveness are assessed separately, because they answer
          different questions and fail in different ways. Every workpaper records how the
          sample was chosen — a sample without a rationale is an opinion.
        </p>

        {summary && (
          <>
            <div className="tiles">
              <div className="tile">
                <span className="tile-value">{summary.total_tests}</span>
                <span className="tile-label">workpapers</span>
              </div>
              <div className="tile">
                <span className="tile-value">{summary.percent_controls_tested}%</span>
                <span className="tile-label">
                  of controls tested ({summary.controls_tested}/{summary.controls_total})
                </span>
              </div>
              <div className={`tile ${summary.open_findings > 0 ? 'tile-alert' : ''}`}>
                <span className="tile-value">{summary.open_findings}</span>
                <span className="tile-label">open findings</span>
              </div>
              <div className={`tile ${summary.controls_design_deficient > 0 ? 'tile-alert' : ''}`}>
                <span className="tile-value">{summary.controls_design_deficient}</span>
                <span className="tile-label">design deficient</span>
              </div>
              <div className={`tile ${summary.rationales_outstanding > 0 ? 'tile-todo' : ''}`}>
                <span className="tile-value">{summary.rationales_outstanding}</span>
                <span className="tile-label">rationales outstanding</span>
              </div>
            </div>

            {summary.optimistic_risk_links.length > 0 && (
              <div className="banner banner-warn" role="note">
                <strong>
                  {summary.optimistic_risk_links.length} risk-control link
                  {summary.optimistic_risk_links.length === 1 ? '' : 's'} claim more assurance
                  than the control library supports:
                </strong>{' '}
                {summary.optimistic_risk_links.join(', ')}. This is surfaced rather than
                blocked — an analyst may be scoping to a population the exceptions did not
                touch, but the discrepancy should be visible.
              </div>
            )}
          </>
        )}

        <div className="framework-switch">
          {(['tests', 'controls', 'findings'] as Tab[]).map((option) => (
            <button
              key={option}
              type="button"
              className={option === tab ? 'active' : ''}
              onClick={() => {
                setTab(option)
                setSelected(null)
              }}
            >
              {option === 'tests'
                ? 'Workpapers'
                : option === 'controls'
                  ? 'Control effectiveness'
                  : 'Findings'}
            </button>
          ))}
        </div>

        {tab === 'tests' && (
          <table className="register">
            <thead>
              <tr>
                <th>Test</th>
                <th>Control</th>
                <th className="num">Population</th>
                <th className="num">Sample</th>
                <th>Method</th>
                <th className="num">Exceptions</th>
                <th>Conclusion</th>
                <th>Finding</th>
              </tr>
            </thead>
            <tbody>
              {sortedTests.map((test) => (
                <tr key={test.test_ref}>
                  <td className="cell-ref">
                    <button type="button" onClick={() => setSelected(test.test_ref)}>
                      {test.test_ref}
                    </button>
                  </td>
                  <td>
                    <code>{test.control_id}</code> {test.control_title}
                    <span className="row-sub">
                      {test.tester} · {test.test_date}
                      {test.rationale_outstanding && (
                        <span className="tag tag-todo">rationale outstanding</span>
                      )}
                      {!test.is_reviewed && <span className="tag tag-warn">unreviewed</span>}
                    </span>
                  </td>
                  <td className="num">{test.population_size}</td>
                  <td className="num">{test.sample_size}</td>
                  <td>{SAMPLE_METHOD_LABEL[test.sample_selection_method]}</td>
                  <td className="num">{test.exceptions_count}</td>
                  <td>
                    <span className={`concl concl-${test.conclusion.toLowerCase()}`}>
                      {CONCLUSION_LABEL[test.conclusion]}
                    </span>
                  </td>
                  <td>{test.linked_finding_ref ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === 'controls' && (
          <>
            <p className="muted rule-note" title={EFFECTIVENESS_RULE}>
              Hover for the design/operating rule. ⓘ
            </p>
            <table className="register">
              <thead>
                <tr>
                  <th>Control</th>
                  <th>Family</th>
                  <th title={EFFECTIVENESS_RULE}>Design</th>
                  <th title={EFFECTIVENESS_RULE}>Operating</th>
                  <th className="num">Tests</th>
                  <th>Supports at most</th>
                </tr>
              </thead>
              <tbody>
                {(controls.data ?? []).map((control) => (
                  <tr key={control.control_id}>
                    <td>
                      <code>{control.control_id}</code> {control.title}
                      {control.effectiveness_note && (
                        <span className="row-sub">{control.effectiveness_note}</span>
                      )}
                    </td>
                    <td>{control.control_family}</td>
                    <td>
                      <span
                        className={`impl impl-${control.design_effectiveness === 'EFFECTIVE' ? 'implemented' : control.design_effectiveness === 'DEFICIENT' ? 'not_implemented' : 'partially_implemented'}`}
                        title={EFFECTIVENESS_RULE}
                      >
                        {DESIGN_LABEL[control.design_effectiveness]}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`basis basis-${control.operating_effectiveness === 'EFFECTIVE' ? 'tested_effective' : control.operating_effectiveness === 'EFFECTIVE_WITH_EXCEPTIONS' ? 'tested_with_exceptions' : control.operating_effectiveness === 'INEFFECTIVE' ? 'tested_ineffective' : 'not_tested'}`}
                        title={EFFECTIVENESS_RULE}
                      >
                        {OPERATING_LABEL[control.operating_effectiveness]}
                      </span>
                    </td>
                    <td className="num">{control.test_count}</td>
                    <td className="muted">
                      {BASIS_LABEL[control.strongest_supported_basis]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {tab === 'findings' && (
          <div className="findings">
            {(findings.data ?? []).map((finding) => (
              <article key={finding.finding_ref} className="finding-card">
                <div className="chain-row">
                  <code className="chain-ref">{finding.finding_ref}</code>
                  <span className={`sev sev-${finding.severity.toLowerCase()}`}>
                    {finding.severity.toLowerCase()}
                  </span>
                  <span className="muted">{finding.status.toLowerCase()}</span>
                  {finding.source_test_ref && (
                    <span className="muted">from {finding.source_test_ref}</span>
                  )}
                </div>
                <h3>{finding.title}</h3>
                <p>{finding.description}</p>
                <p className="muted">
                  Identified {finding.identified_date} by {finding.identified_by} · owner{' '}
                  {finding.owner}
                </p>
                {finding.remediation.map((item) => (
                  <p key={item.remediation_ref} className="muted">
                    → <code>{item.remediation_ref}</code> {item.title} · {item.owner} · due{' '}
                    {item.due_date}
                    {item.overdue && <span className="tag tag-breach">overdue</span>}
                  </p>
                ))}
                <AiAssistant
                  title={`AI remediation assistant for ${finding.finding_ref}`}
                  lede="Correction and corrective action are drafted as separate things,
                        because Clause 10.2 asks for both. No owner is assigned and no
                        date is proposed."
                  actions={[
                    {
                      key: `remediation-${finding.finding_ref}`,
                      label: 'Suggest correction and corrective action',
                      hint: 'Plus the evidence that would justify closing it',
                      run: (question) =>
                        aiApi.remediationAssist(finding.finding_ref, question),
                      render: (result: AiEnvelope) => (
                        <RemediationBody data={result as AiRemediationAssist} />
                      ),
                    },
                  ]}
                />
              </article>
            ))}
          </div>
        )}
      </div>

      {selected && <Workpaper testRef={selected} onClose={() => setSelected(null)} />}
    </section>
  )
}
