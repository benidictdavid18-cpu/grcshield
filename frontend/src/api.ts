import { getToken, handleUnauthorised } from './auth'

const BASE = '/api'

export type ScopeStatus = 'PRIMARY' | 'SECONDARY' | 'ROADMAP'
export type MappingRelationship = 'EQUIVALENT' | 'PARTIAL' | 'SUPPORTING'

export interface Framework {
  id: number
  code: string
  name: string
  version: string
  publisher: string
  scope_status: ScopeStatus
  scope_note: string
  control_count: number
}

export interface GroupSummary {
  group_ref: string
  group_title: string
  total: number
  in_scope: number
  out_of_scope: number
}

export interface FrameworkDetail extends Framework {
  groups: GroupSummary[]
}

export interface Control {
  id: number
  control_ref: string
  title: string
  group_ref: string
  group_title: string
  in_scope: boolean
  scope_note: string | null
}

export interface MappedCriterion {
  control_ref: string
  title: string
  group_ref: string
  group_title: string
  relationship_type: MappingRelationship
}

export interface ControlDetail extends Control {
  framework_code: string
  mappings: MappedCriterion[]
}

export interface Report {
  code: string
  title: string
  audience: string
  decision_supported: string
  available_from_phase: number
  implemented: boolean
  endpoint: string | null
}

export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type EffectivenessBasis =
  | 'NOT_TESTED'
  | 'DESIGN_ONLY'
  | 'TESTED_EFFECTIVE'
  | 'TESTED_WITH_EXCEPTIONS'
  | 'TESTED_INEFFECTIVE'
export type TreatmentDecision = 'MITIGATE' | 'ACCEPT' | 'TRANSFER' | 'AVOID'
export type RiskStatus = 'OPEN' | 'TREATMENT_IN_PROGRESS' | 'MONITORING' | 'CLOSED'

export interface Score {
  likelihood: number
  impact: number
  score: number
  band: RiskBand
}

export interface AppetiteComparison {
  max_acceptable_band: RiskBand | null
  approver_role: string | null
  exceeds_appetite: boolean | null
}

export interface RiskSummary {
  risk_ref: string
  title: string
  category: string
  category_label: string
  owner_role: string
  status: RiskStatus
  treatment_decision: TreatmentDecision
  inherent: Score
  residual: Score
  appetite: AppetiteComparison
  justification_outstanding: boolean
  has_uncredited_controls: boolean
}

export interface LinkedControl {
  control_id: string
  title: string
  control_family: string
  owner_role: string
  annex_a_refs: string[]
  effectiveness_basis: EffectivenessBasis
  credits_reduction: boolean
  note: string | null
}

export interface RiskDetail extends RiskSummary {
  description: string
  asset: string
  threat: string
  vulnerability: string
  residual_justification: string
  treatment_summary: string
  date_identified: string
  last_reviewed: string | null
  next_review: string | null
  controls: LinkedControl[]
}

export interface BandBoundary {
  band: RiskBand
  min_score: number
  max_score: number
}

export interface RegisterSummary {
  total: number
  by_residual_band: Record<string, number>
  exceeding_appetite: number
  justifications_outstanding: number
  bands: BandBoundary[]
}

export interface Appetite {
  category: string
  category_label: string
  max_acceptable_band: RiskBand
  approver_role: string
  rationale: string
  last_reviewed: string | null
}

export type ImplementationStatus =
  | 'NOT_IMPLEMENTED'
  | 'PARTIALLY_IMPLEMENTED'
  | 'IMPLEMENTED'
export type RemediationStatus =
  | 'OPEN'
  | 'IN_PROGRESS'
  | 'BLOCKED'
  | 'COMPLETED'
  | 'CANCELLED'
export type RemediationPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface SoASummary {
  control_ref: string
  control_title: string
  theme: string
  applicable: boolean
  implementation_status: ImplementationStatus
  owner: string
  is_gap: boolean
  justification_outstanding: boolean
  linked_risk_count: number
  linked_control_count: number
  linked_evidence_count: number
  open_remediation_count: number
  has_expired_evidence: boolean
}

export interface SoALinkedRisk {
  risk_ref: string
  title: string
  category_label: string
  treatment_decision: TreatmentDecision
  residual_score: number
  residual_band: RiskBand
  exceeds_appetite: boolean | null
}

export interface SoALinkedControl {
  control_id: string
  title: string
  owner_role: string
  control_family: string
}

export interface EvidenceArtifact {
  evidence_ref: string
  title: string
  description: string
  evidence_type: string
  source_system: string
  collected_by: string
  collected_date: string
  valid_from: string
  valid_until: string
  file_reference: string | null
  control_id: string | null
  expired: boolean
}

export interface RemediationRecord {
  remediation_ref: string
  title: string
  description: string
  owner: string
  due_date: string
  status: RemediationStatus
  priority: RemediationPriority
  completed_date: string | null
  overdue: boolean
}

export interface SoADetail extends SoASummary {
  justification_inclusion: string | null
  justification_exclusion: string | null
  implementation_description: string | null
  last_reviewed: string | null
  next_review: string | null
  approved_by: string | null
  approved_date: string | null
  version: string
  risks: SoALinkedRisk[]
  controls: SoALinkedControl[]
  tests: {
    test_ref: string
    control_id: string
    test_date: string
    conclusion: string
    exceptions_count: number
    sample_size: number
    population_size: number
    finding_ref: string | null
  }[]
  evidence: EvidenceArtifact[]
  remediation: RemediationRecord[]
  validation_errors: string[]
}

export interface ThemeSummary {
  theme: string
  theme_title: string
  total: number
  applicable: number
  excluded: number
  implemented: number
  partially_implemented: number
  not_implemented: number
}

export interface SoAOverview {
  total_controls: number
  applicable: number
  excluded: number
  implemented: number
  partially_implemented: number
  not_implemented: number
  percent_implemented: number
  gaps: number
  justifications_outstanding: number
  implemented_without_evidence: number
  expired_evidence: number
  open_remediation: number
  overdue_remediation: number
  version: string
  approved_by: string | null
  approved_date: string | null
  themes: ThemeSummary[]
}

export type DesignEffectiveness = 'NOT_ASSESSED' | 'EFFECTIVE' | 'DEFICIENT'
export type OperatingEffectiveness =
  | 'NOT_TESTED'
  | 'EFFECTIVE'
  | 'EFFECTIVE_WITH_EXCEPTIONS'
  | 'INEFFECTIVE'
export type TestConclusion = 'PASS' | 'PASS_WITH_EXCEPTIONS' | 'FAIL'
export type SampleMethod = 'RANDOM' | 'HAPHAZARD' | 'JUDGMENTAL' | 'FULL_POPULATION'
export type FindingSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type FindingStatus = 'DRAFT' | 'OPEN' | 'REMEDIATED' | 'CLOSED'

export interface InternalControl {
  control_id: string
  title: string
  description: string
  control_family: string
  owner_role: string
  annex_a_refs: string[]
  design_effectiveness: DesignEffectiveness
  operating_effectiveness: OperatingEffectiveness
  effectiveness_note: string | null
  last_tested: string | null
  test_count: number
  strongest_supported_basis: EffectivenessBasis
}

export interface ControlTestSummary {
  test_ref: string
  control_id: string
  control_title: string
  tester: string
  test_date: string
  period_covered_start: string
  period_covered_end: string
  population_size: number
  sample_size: number
  sample_selection_method: SampleMethod
  exceptions_count: number
  exception_rate: number
  conclusion: TestConclusion
  reviewed_by: string | null
  is_reviewed: boolean
  rationale_outstanding: boolean
  linked_finding_ref: string | null
}

export interface ControlTestDetail extends ControlTestSummary {
  test_objective: string
  test_procedure: string
  population_description: string
  sampling_rationale: string
  results_summary: string
  exception_details: string | null
  review_date: string | null
  evidence: { evidence_ref: string; title: string; expired: boolean }[]
}

export interface Finding {
  finding_ref: string
  title: string
  description: string
  severity: FindingSeverity
  status: FindingStatus
  source: string
  identified_date: string
  identified_by: string
  owner: string
  closed_date: string | null
  control_id: string | null
  source_test_ref: string | null
  remediation: {
    remediation_ref: string
    title: string
    owner: string
    due_date: string
    status: string
    overdue: boolean
  }[]
}

export interface TestingOverview {
  total_tests: number
  by_conclusion: Record<string, number>
  controls_tested: number
  controls_total: number
  percent_controls_tested: number
  tests_unreviewed: number
  rationales_outstanding: number
  open_findings: number
  findings_by_severity: Record<string, number>
  controls_design_deficient: number
  controls_never_tested: number
  optimistic_risk_links: string[]
}

export interface InternalAudit {
  audit_ref: string
  title: string
  scope: string
  objectives: string
  criteria: string
  auditor: string
  independence_note: string
  planned_start: string
  planned_end: string
  actual_start: string | null
  actual_end: string | null
  status: string
  outcome_summary: string | null
}

export interface ManagementReviewRecord {
  review_ref: string
  review_date: string
  chair: string
  attendees: string
  inputs_considered: string
  decisions: string
  actions: string
  next_review_date: string | null
}

export interface NonconformityRecord {
  nc_ref: string
  description: string
  source: string
  identified_date: string
  identified_by: string
  owner: string
  immediate_correction: string
  root_cause_analysis: string | null
  corrective_action: string | null
  target_date: string | null
  effectiveness_check_date: string | null
  effectiveness_check_result: string | null
  status: string
  closure_date: string | null
  finding_ref: string | null
}

export interface AssetRecord {
  asset_ref: string
  name: string
  description: string
  asset_type: string
  classification: string
  owner_role: string
  hosting_location: string
  holds_personal_data: boolean
}

export interface LinkedRiskBrief {
  risk_ref: string
  title: string
  residual_score: number
  residual_band: RiskBand
  exceeds_appetite: boolean | null
}

export interface ControlBrief {
  control_id: string
  title: string
  operating_effectiveness: string
  credited: boolean
}

export interface RiskExceptionRecord {
  exception_ref: string
  risk_ref: string
  risk_title: string
  risk_owner_role: string
  residual_band: RiskBand
  exceeds_appetite: boolean | null
  requested_by: string
  business_justification: string
  compensating_controls: string
  approver_role: string
  approval_date: string | null
  expiry_date: string
  review_trigger: string
  status: string
  state: string
  days_remaining: number
  decision_note: string | null
}

export interface ExceptionSummary {
  total: number
  live: number
  expired: number
  expiring_soon: number
  rejected_or_withdrawn: number
  expiry_warning_days: number
  uncovered_breaches: string[]
}

export interface RopaRecord {
  ropa_ref: string
  processing_activity: string
  purpose: string
  lawful_basis: string
  legitimate_interests_assessment: string | null
  data_subject_categories: string
  personal_data_categories: string
  special_category_data: boolean
  recipients: string
  transfers_outside_eea: boolean
  transfer_detail: string | null
  transfer_safeguard: string
  retention_period: string
  security_measures_summary: string
  controller_role: string
  owner_role: string
  last_reviewed: string | null
  assets: AssetRecord[]
  risks: LinkedRiskBrief[]
  controls: ControlBrief[]
  dpia_refs: string[]
}

export interface DpiaRecord {
  dpia_ref: string
  title: string
  ropa_ref: string | null
  trigger_reason: string
  processing_description: string
  necessity_and_proportionality: string
  risks_to_data_subjects: string
  mitigating_measures: string
  residual_risk: string
  residual_risk_note: string
  dpo_consulted: boolean
  dpo_advice: string | null
  supervisory_authority_consulted: boolean
  data_subjects_consulted: boolean
  outcome: string
  assessed_by: string
  assessment_date: string
  review_date: string | null
  review_overdue: boolean
  assets: AssetRecord[]
  risks: LinkedRiskBrief[]
}

export interface BiaRecord {
  bia_ref: string
  process_name: string
  process_description: string
  owner_role: string
  rto_hours: number
  rpo_hours: number
  mtpd_hours: number
  recovery_headroom_hours: number
  currency: string
  impact_1h: number
  impact_24h: number
  impact_1w: number
  impact_note: string
  workaround: string
  recovery_note: string | null
  last_reviewed: string | null
  assets: AssetRecord[]
  controls: ControlBrief[]
  risks: LinkedRiskBrief[]
}

export interface PrivacyOverview {
  ropa_entries: number
  activities_with_transfers: number
  activities_on_legitimate_interests: number
  dpias: number
  dpias_high_residual: number
  dpias_review_overdue: number
  dpias_awaiting_supervisory_consultation: number
  assets: number
  assets_holding_personal_data: number
}

export type KriBand = 'GREEN' | 'AMBER' | 'RED' | 'NO_DATA'

export interface TrendPoint {
  period_end: string
  value: number | null
  band: KriBand
  is_current: boolean
}

export interface Kri {
  kri_ref: string
  name: string
  formula_description: string
  data_source: string
  rationale: string
  unit: 'PERCENT' | 'COUNT' | 'DAYS'
  direction: 'HIGHER_IS_BETTER' | 'LOWER_IS_BETTER'
  green_threshold: number
  amber_threshold: number
  owner_role: string
  measurement_frequency: string
  current_value: number | null
  current_band: KriBand
  current_detail: string
  trend: TrendPoint[]
  movement: 'IMPROVING' | 'DETERIORATING' | 'FLAT' | 'NO_TREND'
}

export interface ExecutiveSummary {
  as_of: string
  posture_statement: string
  posture_key: string
  risks_total: number
  risks_beyond_agreed_limit: number
  risks_carried_without_a_decision: number
  safeguards_required: number
  safeguards_in_place: number
  safeguards_percent: number
  top_risks: {
    risk_ref: string
    plain_title: string
    what_could_happen: string
    who_owns_it: string
    beyond_agreed_limit: boolean
  }[]
  top_gaps: {
    what_is_missing: string
    detail: string
    risks_depending_on_it: number
    owner: string
  }[]
  open_findings_by_severity: Record<string, number>
  open_findings_total: number
  remediation_open: number
  remediation_overdue: number
  third_party: { risks_tracked: number; beyond_agreed_limit: number; summary: string }
  categories: Record<string, number>
  priorities: { headline: string; why: string; owner: string; by_when: string }[]
}

export interface Health {
  status: string
  database: string
  annex_a_controls: number
  annex_a_expected: number
  seeded: boolean
  environment: string
  disclaimer: string
}

async function get<T>(path: string): Promise<T> {
  const token = getToken()
  const response = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (response.status === 401) {
    // An expired token should return to the sign-in screen, not leave a blank page.
    handleUnauthorised()
    throw new Error('Your session has expired. Please sign in again.')
  }
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${path}`)
  }
  return (await response.json()) as T
}

export const api = {
  health: () => get<Health>('/health'),
  frameworks: () => get<Framework[]>('/frameworks'),
  framework: (code: string) => get<FrameworkDetail>(`/frameworks/${code}`),
  controls: (code: string, params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    return get<Control[]>(`/frameworks/${code}/controls${query ? `?${query}` : ''}`)
  },
  control: (code: string, ref: string) => get<ControlDetail>(`/frameworks/${code}/controls/${ref}`),
  reports: () => get<Report[]>('/reports'),
  risks: (params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    return get<RiskSummary[]>(`/risks${query ? `?${query}` : ''}`)
  },
  risk: (ref: string) => get<RiskDetail>(`/risks/${ref}`),
  riskSummary: () => get<RegisterSummary>('/risks/summary'),
  appetite: () => get<Appetite[]>('/risk-appetite'),
  soa: (params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    return get<SoASummary[]>(`/soa${query ? `?${query}` : ''}`)
  },
  soaEntry: (ref: string) => get<SoADetail>(`/soa/${ref}`),
  soaOverview: () => get<SoAOverview>('/soa/overview'),
  soaReportUrl: () => `${BASE}/soa/report.pdf`,
  internalControls: () => get<InternalControl[]>('/internal-controls'),
  controlTests: (params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    return get<ControlTestSummary[]>(`/control-tests${query ? `?${query}` : ''}`)
  },
  controlTest: (ref: string) => get<ControlTestDetail>(`/control-tests/${ref}`),
  testingOverview: () => get<TestingOverview>('/control-tests/overview'),
  findings: () => get<Finding[]>('/findings'),
  internalAudits: () => get<InternalAudit[]>('/isms/audits'),
  managementReviews: () => get<ManagementReviewRecord[]>('/isms/management-reviews'),
  nonconformities: () => get<NonconformityRecord[]>('/isms/nonconformities'),
  ismsRecordsUrl: () => `${BASE}/isms/records.pdf`,
  assets: () => get<AssetRecord[]>('/assets'),
  riskExceptions: () => get<RiskExceptionRecord[]>('/risk-exceptions'),
  exceptionSummary: () => get<ExceptionSummary>('/risk-exceptions/summary'),
  ropa: () => get<RopaRecord[]>('/ropa'),
  dpias: () => get<DpiaRecord[]>('/dpias'),
  privacyOverview: () => get<PrivacyOverview>('/privacy/overview'),
  bia: () => get<BiaRecord[]>('/bia'),
  kris: () => get<Kri[]>('/kris'),
  executiveSummary: () => get<ExecutiveSummary>('/executive-summary'),
  riskRegisterReportUrl: () => `${BASE}/reports/risk-register.pdf`,
  executiveReportUrl: () => `${BASE}/reports/executive-summary.pdf`,
}

/** PDF links cannot carry an Authorization header, so fetch and open as a blob. */
export async function openReport(url: string): Promise<void> {
  const token = getToken()
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (response.status === 401) {
    handleUnauthorised()
    return
  }
  if (!response.ok) throw new Error(`Could not open report (${response.status}).`)
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  window.open(objectUrl, '_blank', 'noopener')
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}
