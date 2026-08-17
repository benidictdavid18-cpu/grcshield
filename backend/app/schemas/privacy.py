from datetime import date

from pydantic import BaseModel, ConfigDict

from app.services.privacy_continuity import (
    AssetType,
    Classification,
    DpiaOutcome,
    ExceptionStatus,
    LawfulBasis,
    ResidualRiskLevel,
    TransferSafeguard,
)
from app.services.risk_scoring import RiskBand


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_ref: str
    name: str
    description: str
    asset_type: AssetType
    classification: Classification
    owner_role: str
    hosting_location: str
    holds_personal_data: bool


class LinkedRiskBrief(BaseModel):
    risk_ref: str
    title: str
    residual_score: int
    residual_band: RiskBand
    exceeds_appetite: bool | None = None


class ControlBrief(BaseModel):
    control_id: str
    title: str
    operating_effectiveness: str
    credited: bool


class ExceptionOut(BaseModel):
    exception_ref: str
    risk_ref: str
    risk_title: str
    risk_owner_role: str
    residual_band: RiskBand
    exceeds_appetite: bool | None = None
    requested_by: str
    business_justification: str
    compensating_controls: str
    approver_role: str
    approval_date: date | None = None
    expiry_date: date
    review_trigger: str
    status: ExceptionStatus
    state: str
    days_remaining: int
    decision_note: str | None = None


class ExceptionSummaryOut(BaseModel):
    total: int
    live: int
    expired: int
    expiring_soon: int
    rejected_or_withdrawn: int
    expiry_warning_days: int
    uncovered_breaches: list[str]


class ExceptionCreateIn(BaseModel):
    risk_ref: str
    requested_by: str
    business_justification: str
    compensating_controls: str
    approver_role: str
    approval_date: date | None = None
    expiry_date: date | None = None
    review_trigger: str = ""
    status: ExceptionStatus = ExceptionStatus.PENDING


class RopaOut(BaseModel):
    ropa_ref: str
    processing_activity: str
    purpose: str
    lawful_basis: LawfulBasis
    legitimate_interests_assessment: str | None = None
    data_subject_categories: str
    personal_data_categories: str
    special_category_data: bool
    recipients: str
    transfers_outside_eea: bool
    transfer_detail: str | None = None
    transfer_safeguard: TransferSafeguard
    retention_period: str
    security_measures_summary: str
    controller_role: str
    owner_role: str
    last_reviewed: date | None = None
    assets: list[AssetOut]
    risks: list[LinkedRiskBrief]
    controls: list[ControlBrief]
    dpia_refs: list[str]


class DpiaOut(BaseModel):
    dpia_ref: str
    title: str
    ropa_ref: str | None = None
    trigger_reason: str
    processing_description: str
    necessity_and_proportionality: str
    risks_to_data_subjects: str
    mitigating_measures: str
    residual_risk: ResidualRiskLevel
    residual_risk_note: str
    dpo_consulted: bool
    dpo_advice: str | None = None
    supervisory_authority_consulted: bool
    data_subjects_consulted: bool
    outcome: DpiaOutcome
    assessed_by: str
    assessment_date: date
    review_date: date | None = None
    review_overdue: bool
    assets: list[AssetOut]
    risks: list[LinkedRiskBrief]


class BiaOut(BaseModel):
    bia_ref: str
    process_name: str
    process_description: str
    owner_role: str
    rto_hours: float
    rpo_hours: float
    mtpd_hours: float
    recovery_headroom_hours: float
    currency: str
    impact_1h: float
    impact_24h: float
    impact_1w: float
    impact_note: str
    workaround: str
    recovery_note: str | None = None
    last_reviewed: date | None = None
    assets: list[AssetOut]
    controls: list[ControlBrief]
    risks: list[LinkedRiskBrief]


class PrivacyOverviewOut(BaseModel):
    ropa_entries: int
    activities_with_transfers: int
    activities_on_legitimate_interests: int
    dpias: int
    dpias_high_residual: int
    dpias_review_overdue: int
    dpias_awaiting_supervisory_consultation: int
    assets: int
    assets_holding_personal_data: int
