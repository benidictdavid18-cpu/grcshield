import type { EffectivenessBasis, RiskStatus, TreatmentDecision } from './api'

export const BASIS_LABEL: Record<EffectivenessBasis, string> = {
  NOT_TESTED: 'Not tested',
  DESIGN_ONLY: 'Design only',
  TESTED_EFFECTIVE: 'Tested — effective',
  TESTED_WITH_EXCEPTIONS: 'Tested — with exceptions',
  TESTED_INEFFECTIVE: 'Tested — ineffective',
}

/** What each basis actually entitles the control to claim. */
export const BASIS_MEANING: Record<EffectivenessBasis, string> = {
  NOT_TESTED:
    'No evidence has been gathered. The control may not be credited with any residual reduction.',
  DESIGN_ONLY:
    'The design has been assessed but operation has not been tested. Credit is permitted but weak.',
  TESTED_EFFECTIVE: 'Tested over a period and found to operate as designed.',
  TESTED_WITH_EXCEPTIONS:
    'Tested and found to operate, but with exceptions. Partial coverage earns partial credit.',
  TESTED_INEFFECTIVE:
    'Tested and found not to operate. A known failure provides less assurance than an open question, so no credit is permitted.',
}

export const TREATMENT_LABEL: Record<TreatmentDecision, string> = {
  MITIGATE: 'Mitigate',
  ACCEPT: 'Accept',
  TRANSFER: 'Transfer',
  AVOID: 'Avoid',
}

export const STATUS_LABEL: Record<RiskStatus, string> = {
  OPEN: 'Open',
  TREATMENT_IN_PROGRESS: 'Treatment in progress',
  MONITORING: 'Monitoring',
  CLOSED: 'Closed',
}

export const TODO_MARKER = 'TODO AUTHOR:BENNY'

export const IMPLEMENTATION_LABEL: Record<string, string> = {
  NOT_IMPLEMENTED: 'Not implemented',
  PARTIALLY_IMPLEMENTED: 'Partially implemented',
  IMPLEMENTED: 'Implemented',
}

export const DESIGN_LABEL: Record<string, string> = {
  NOT_ASSESSED: 'Not assessed',
  EFFECTIVE: 'Effective',
  DEFICIENT: 'Deficient',
}

export const OPERATING_LABEL: Record<string, string> = {
  NOT_TESTED: 'Not tested',
  EFFECTIVE: 'Effective',
  EFFECTIVE_WITH_EXCEPTIONS: 'With exceptions',
  INEFFECTIVE: 'Ineffective',
}

export const CONCLUSION_LABEL: Record<string, string> = {
  PASS: 'Pass',
  PASS_WITH_EXCEPTIONS: 'Pass with exceptions',
  FAIL: 'Fail',
}

export const SAMPLE_METHOD_LABEL: Record<string, string> = {
  RANDOM: 'Random',
  HAPHAZARD: 'Haphazard',
  JUDGMENTAL: 'Judgmental',
  FULL_POPULATION: 'Full population',
}

/** Shown as a tooltip wherever the two effectiveness ratings appear together. */
export const EFFECTIVENESS_RULE =
  'Design and operating effectiveness answer two different questions. Design: if this ' +
  'control ran exactly as written, would it achieve the objective? Operating: did it ' +
  'actually run that way over the period? A control can pass one and fail the other. ' +
  'Operating effectiveness cannot be Effective while the design is Deficient — if the ' +
  'control as designed does not achieve the objective, running it perfectly still does ' +
  'not.'

export const REMEDIATION_LABEL: Record<string, string> = {
  OPEN: 'Open',
  IN_PROGRESS: 'In progress',
  BLOCKED: 'Blocked',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
}
