/* The assistant's client, kept in its own module for the same reason the backend keeps
 * it in its own package: the AI layer sits beside the GRC application rather than
 * inside it, and the file boundary is the cheapest way to keep that true.
 *
 * The browser never talks to Ollama. Every call goes to the FastAPI backend, which owns
 * the system prompt, decides what record content the model may see, and holds the model
 * configuration. A browser calling a model server directly would put the system prompt
 * in the bundle, where anybody could read it and replace it.
 */

import { type ImplementationStatus } from './api'
import { getToken, handleUnauthorised } from './auth'

const BASE = '/api'

export type AiFeature =
  | 'RISK_ASSIST'
  | 'RISK_DESCRIPTION'
  | 'CONTROL_MAPPING'
  | 'CONTROL_TEST_ASSIST'
  | 'FINDING_DRAFT'
  | 'REMEDIATION_ASSIST'
  | 'POLICY_DRAFT'
  | 'CONSISTENCY_SWEEP'

export type AiConfidence = 'low' | 'medium' | 'high'

export interface AiContextItem {
  label: string
  value: string
}

/** Fields every suggestion carries, whatever was asked. */
export interface AiSuggestionBase {
  summary: string
  observations: string[]
  suggestions: string[]
  missing_information: string[]
  confidence: AiConfidence
}

export interface AiEnvelope {
  feature: AiFeature
  advisory: boolean
  requires_human_review: boolean
  label: string
  note: string
  provider: string
  model: string
  generated_at: string
  latency_ms: number
  entity_type: string | null
  entity_ref: string | null
  context_provided: AiContextItem[]
  guardrail_notes: string[]
  interaction_ref: string | null
}

export interface RiskAssistSuggestion extends AiSuggestionBase {
  threat_scenarios: string[]
  vulnerabilities: string[]
  control_areas: string[]
  questions_to_investigate: string[]
  treatment_options: string[]
}

export interface RiskDescriptionSuggestion extends AiSuggestionBase {
  threat: string
  vulnerability: string
  event: string
  impact: string
  risk_statement: string
}

export interface ResolvedControl {
  control_ref: string
  title: string
  reason: string
  already_linked: boolean
  soa_applicable: boolean | null
  soa_implementation_status: ImplementationStatus | null
}

export interface ControlTestSuggestion extends AiSuggestionBase {
  evidence_summary: string
  possible_exceptions: string[]
  missing_evidence: string[]
  follow_up_questions: string[]
  why_it_might_matter: string[]
  additional_testing: string[]
}

export interface FindingDraftSuggestion extends AiSuggestionBase {
  draft_title: string
  condition: string
  criteria: string
  risk_and_impact: string
  possible_root_causes: string[]
  suggested_remediation_language: string
}

export interface RemediationSuggestion extends AiSuggestionBase {
  correction: string
  corrective_action: string
  root_cause_questions: string[]
  remediation_steps: string[]
  evidence_required_to_close: string[]
  suggested_owner_role: string
  priority_rationale: string
}

export interface PolicyDraftSuggestion extends AiSuggestionBase {
  document_title: string
  purpose: string
  scope: string
  sections: { heading: string; body: string }[]
  open_questions: string[]
}

export interface AiRiskAssist extends AiEnvelope {
  suggestion: RiskAssistSuggestion
}
export interface AiRiskDescription extends AiEnvelope {
  suggestion: RiskDescriptionSuggestion
}
export interface AiControlMapping extends AiEnvelope {
  suggestion: AiSuggestionBase & { suggested_controls: { control: string; reason: string }[] }
  resolved_controls: ResolvedControl[]
  rejected_controls: string[]
}
export interface AiControlTestAssist extends AiEnvelope {
  suggestion: ControlTestSuggestion
}
export interface AiFindingDraft extends AiEnvelope {
  suggestion: FindingDraftSuggestion
}
export interface AiRemediationAssist extends AiEnvelope {
  suggestion: RemediationSuggestion
}
export interface AiPolicyDraft extends AiEnvelope {
  suggestion: PolicyDraftSuggestion
}

export interface Contradiction {
  records: string[]
  what_disagrees: string
  why_it_matters: string
  question_for_the_analyst: string
}

export interface ConsistencySweepSuggestion extends AiSuggestionBase {
  contradictions: Contradiction[]
  consistent_aspects: string[]
}

export interface AiConsistencySweep extends AiEnvelope {
  suggestion: ConsistencySweepSuggestion
  uncited_records: string[]
  records_compared: string[]
}

/** A control the rules say is worth asking about. Computed without the model. */
export interface SweepCandidate {
  control_id: string
  title: string
  record_count: number
  record_types: string[]
  reasons: string[]
}

export interface AiStatus {
  enabled: boolean
  ready: boolean
  provider: string
  configured_model: string
  reachable: boolean
  model_available: boolean
  detail: string
  available_models: string[]
  version: string | null
  host_is_local: boolean
  checked_at: string
  core_functionality_requires_ai: boolean
}

export interface AiInteraction {
  interaction_ref: string
  created_at: string
  username: string
  user_role: string
  feature: AiFeature
  entity_type: string | null
  entity_ref: string | null
  provider: string
  model: string
  status: string
  latency_ms: number | null
  prompt_chars: number
  response_chars: number | null
  response_digest: string | null
  guardrail_flags: string | null
  error_note: string | null
}

export type PolicyDocumentType =
  | 'POLICY'
  | 'PROCEDURE'
  | 'CONTROL_DESCRIPTION'
  | 'EVIDENCE_REQUEST'
  | 'COMPLIANCE_QUESTIONNAIRE'

/** A failure the UI can render as a sentence rather than a stack trace. */
export class AiRequestError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'AiRequestError'
    this.status = status
  }

  /** 503 is an ordinary state -- the assistant is off or Ollama is not running --
   *  and it deserves a calmer message than a genuine fault. */
  get isUnavailable(): boolean {
    return this.status === 503
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: 'Bearer ' + token } : {}
}

async function readError(response: Response): Promise<string> {
  try {
    const problem = await response.json()
    if (typeof problem.detail === 'string') return problem.detail
    if (Array.isArray(problem.detail)) {
      return problem.detail
        .map((entry: { msg?: string; message?: string }) => entry.msg ?? entry.message ?? '')
        .filter(Boolean)
        .join(' ')
    }
  } catch {
    /* A non-JSON error body is still an error; the status line will do. */
  }
  return response.status + ' ' + response.statusText
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(BASE + path, { headers: authHeaders() })
  if (response.status === 401) {
    handleUnauthorised()
    throw new AiRequestError('Your session has expired. Please sign in again.', 401)
  }
  if (!response.ok) throw new AiRequestError(await readError(response), response.status)
  return (await response.json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  if (response.status === 401) {
    handleUnauthorised()
    throw new AiRequestError('Your session has expired. Please sign in again.', 401)
  }
  if (!response.ok) throw new AiRequestError(await readError(response), response.status)
  return (await response.json()) as T
}

export const aiApi = {
  status: (refresh = false) => getJson<AiStatus>('/ai/status' + (refresh ? '?refresh=true' : '')),
  riskAssist: (riskRef: string, question?: string) =>
    postJson<AiRiskAssist>('/ai/risk-assist', { risk_ref: riskRef, question: question || null }),
  riskDescription: (body: {
    risk_ref?: string
    asset?: string
    threat?: string
    vulnerability?: string
    event?: string
    impact?: string
    question?: string
  }) => postJson<AiRiskDescription>('/ai/risk-description', body),
  controlMapping: (riskRef: string, question?: string) =>
    postJson<AiControlMapping>('/ai/control-mapping', {
      risk_ref: riskRef,
      question: question || null,
    }),
  controlTestAssist: (testRef: string, question?: string) =>
    postJson<AiControlTestAssist>('/ai/control-test-assist', {
      test_ref: testRef,
      question: question || null,
    }),
  findingDraft: (testRef: string, question?: string) =>
    postJson<AiFindingDraft>('/ai/finding-draft', {
      test_ref: testRef,
      question: question || null,
    }),
  remediationAssist: (findingRef: string, question?: string) =>
    postJson<AiRemediationAssist>('/ai/remediation-assist', {
      finding_ref: findingRef,
      question: question || null,
    }),
  policyDraft: (body: {
    document_type: PolicyDocumentType
    topic: string
    annex_a_refs?: string[]
    question?: string
  }) => postJson<AiPolicyDraft>('/ai/policy-draft', body),
  consistencyCandidates: () => getJson<SweepCandidate[]>('/ai/consistency-candidates'),
  consistencySweep: (controlId: string, question?: string) =>
    postJson<AiConsistencySweep>('/ai/consistency-sweep', {
      control_id: controlId,
      question: question || null,
    }),
  interactions: (params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params).toString()
    return getJson<AiInteraction[]>('/ai/interactions' + (query ? '?' + query : ''))
  },
}
