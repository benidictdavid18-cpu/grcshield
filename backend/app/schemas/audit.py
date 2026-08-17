from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.services.control_testing import (
    AuditStatus,
    DesignEffectiveness,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    NonconformityStatus,
    OperatingEffectiveness,
    SampleSelectionMethod,
    TestConclusion,
)
from app.services.risk_scoring import ControlEffectivenessBasis


class InternalControlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    control_id: str
    title: str
    description: str
    control_family: str
    owner_role: str
    annex_a_refs: list[str]
    design_effectiveness: DesignEffectiveness
    operating_effectiveness: OperatingEffectiveness
    effectiveness_note: str | None = None
    last_tested: date | None = None
    test_count: int
    strongest_supported_basis: ControlEffectivenessBasis


class EffectivenessUpdateIn(BaseModel):
    design_effectiveness: DesignEffectiveness | None = None
    operating_effectiveness: OperatingEffectiveness | None = None
    effectiveness_note: str | None = None


class TestEvidenceOut(BaseModel):
    evidence_ref: str
    title: str
    expired: bool


class ControlTestSummaryOut(BaseModel):
    test_ref: str
    control_id: str
    control_title: str
    tester: str
    test_date: date
    period_covered_start: date
    period_covered_end: date
    population_size: int
    sample_size: int
    sample_selection_method: SampleSelectionMethod
    exceptions_count: int
    exception_rate: float
    conclusion: TestConclusion
    reviewed_by: str | None = None
    is_reviewed: bool
    rationale_outstanding: bool
    linked_finding_ref: str | None = None


class ControlTestDetailOut(ControlTestSummaryOut):
    test_objective: str
    test_procedure: str
    population_description: str
    sampling_rationale: str
    results_summary: str
    exception_details: str | None = None
    review_date: date | None = None
    evidence: list[TestEvidenceOut]


class ControlTestCreateIn(BaseModel):
    """A new workpaper.

    A FAIL or PASS_WITH_EXCEPTIONS conclusion auto-creates a draft finding and a
    remediation item; there is no field to opt out of that.
    """

    control_id: str
    tester: str = Field(min_length=1)
    test_date: date
    period_covered_start: date
    period_covered_end: date
    test_objective: str = Field(min_length=1)
    test_procedure: str = Field(min_length=1)
    population_description: str = Field(min_length=1)
    population_size: int
    sample_size: int
    sample_selection_method: SampleSelectionMethod
    sampling_rationale: str = ""
    results_summary: str = Field(min_length=1)
    exceptions_count: int = 0
    exception_details: str | None = None
    conclusion: TestConclusion
    reviewed_by: str | None = None
    review_date: date | None = None
    evidence_refs: list[str] = []
    remediation_owner: str | None = None
    remediation_due_date: date | None = None


class LinkedRemediationOut(BaseModel):
    remediation_ref: str
    title: str
    owner: str
    due_date: date
    status: str
    overdue: bool


class FindingOut(BaseModel):
    finding_ref: str
    title: str
    description: str
    severity: FindingSeverity
    status: FindingStatus
    source: FindingSource
    identified_date: date
    identified_by: str
    owner: str
    closed_date: date | None = None
    control_id: str | None = None
    source_test_ref: str | None = None
    remediation: list[LinkedRemediationOut]


class InternalAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_ref: str
    title: str
    scope: str
    objectives: str
    criteria: str
    auditor: str
    independence_note: str
    planned_start: date
    planned_end: date
    actual_start: date | None = None
    actual_end: date | None = None
    status: AuditStatus
    outcome_summary: str | None = None


class ManagementReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_ref: str
    review_date: date
    chair: str
    attendees: str
    inputs_considered: str
    decisions: str
    actions: str
    next_review_date: date | None = None


class NonconformityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nc_ref: str
    description: str
    source: FindingSource
    identified_date: date
    identified_by: str
    owner: str
    immediate_correction: str
    root_cause_analysis: str | None = None
    corrective_action: str | None = None
    target_date: date | None = None
    effectiveness_check_date: date | None = None
    effectiveness_check_result: str | None = None
    status: NonconformityStatus
    closure_date: date | None = None
    finding_ref: str | None = None


class TestingOverviewOut(BaseModel):
    total_tests: int
    by_conclusion: dict[str, int]
    controls_tested: int
    controls_total: int
    percent_controls_tested: float
    tests_unreviewed: int
    rationales_outstanding: int
    open_findings: int
    findings_by_severity: dict[str, int]
    controls_design_deficient: int
    controls_never_tested: int
    optimistic_risk_links: list[str]
