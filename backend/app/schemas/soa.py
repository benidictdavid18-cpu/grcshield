from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.soa import (
    EvidenceType,
    ImplementationStatus,
    RemediationPriority,
    RemediationStatus,
)
from app.services.risk_scoring import RiskBand, TreatmentDecision


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_ref: str
    title: str
    description: str
    evidence_type: EvidenceType
    source_system: str
    collected_by: str
    collected_date: date
    valid_from: date
    valid_until: date
    file_reference: str | None = None
    control_id: str | None = None
    expired: bool


class RemediationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    remediation_ref: str
    title: str
    description: str
    owner: str
    due_date: date
    status: RemediationStatus
    priority: RemediationPriority
    completed_date: date | None = None
    overdue: bool


class LinkedRiskOut(BaseModel):
    risk_ref: str
    title: str
    category_label: str
    treatment_decision: TreatmentDecision
    residual_score: int
    residual_band: RiskBand
    exceeds_appetite: bool | None = None


class LinkedInternalControlOut(BaseModel):
    control_id: str
    title: str
    owner_role: str
    control_family: str


class LinkedTestOut(BaseModel):
    """A workpaper reached through one of this entry's internal controls."""

    test_ref: str
    control_id: str
    test_date: date
    conclusion: str
    exceptions_count: int
    sample_size: int
    population_size: int
    finding_ref: str | None = None


class SoASummaryOut(BaseModel):
    control_ref: str
    control_title: str
    theme: str
    applicable: bool
    implementation_status: ImplementationStatus
    owner: str
    is_gap: bool
    justification_outstanding: bool
    linked_risk_count: int
    linked_control_count: int
    linked_evidence_count: int
    open_remediation_count: int
    has_expired_evidence: bool


class SoADetailOut(SoASummaryOut):
    justification_inclusion: str | None = None
    justification_exclusion: str | None = None
    implementation_description: str | None = None
    last_reviewed: date | None = None
    next_review: date | None = None
    approved_by: str | None = None
    approved_date: date | None = None
    version: str
    risks: list[LinkedRiskOut]
    controls: list[LinkedInternalControlOut]
    tests: list[LinkedTestOut]
    evidence: list[EvidenceOut]
    remediation: list[RemediationOut]
    validation_errors: list[str]


class ThemeSummaryOut(BaseModel):
    theme: str
    theme_title: str
    total: int
    applicable: int
    excluded: int
    implemented: int
    partially_implemented: int
    not_implemented: int


class SoAOverviewOut(BaseModel):
    """The header an auditor reads before anything else."""

    total_controls: int
    applicable: int
    excluded: int
    implemented: int
    partially_implemented: int
    not_implemented: int
    percent_implemented: float
    gaps: int
    justifications_outstanding: int
    implemented_without_evidence: int
    expired_evidence: int
    open_remediation: int
    overdue_remediation: int
    version: str
    approved_by: str | None = None
    approved_date: date | None = None
    themes: list[ThemeSummaryOut]


class SoAUpdateIn(BaseModel):
    """Partial update to an SoA entry.

    Omitted fields keep their current value. The full entry is revalidated after the
    change, so an update that would leave the entry inconsistent is rejected even if
    the offending field was not the one being edited.
    """

    applicable: bool | None = None
    justification_inclusion: str | None = None
    justification_exclusion: str | None = None
    implementation_status: ImplementationStatus | None = None
    implementation_description: str | None = None
    owner: str | None = None
