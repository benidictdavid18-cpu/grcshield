from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.privacy_continuity import (
    AssetType,
    Classification,
    DpiaOutcome,
    LawfulBasis,
    ResidualRiskLevel,
    TransferSafeguard,
)


class Links(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    asset_refs: list[str] = []
    risk_refs: list[str] = []
    control_refs: list[str] = []


class AssetIn(Links):
    name: str = Field(min_length=1, max_length=240)
    description: str
    asset_type: AssetType
    classification: Classification
    owner_role: str = Field(max_length=120)
    hosting_location: str = Field(max_length=160)
    holds_personal_data: bool


class RopaIn(Links):
    processing_activity: str = Field(max_length=240)
    purpose: str
    lawful_basis: LawfulBasis
    legitimate_interests_assessment: str | None = None
    data_subject_categories: str
    personal_data_categories: str
    special_category_data: bool = False
    recipients: str
    transfers_outside_eea: bool = False
    transfer_detail: str | None = None
    transfer_safeguard: TransferSafeguard
    retention_period: str
    security_measures_summary: str
    controller_role: str = Field(max_length=120)
    owner_role: str = Field(max_length=120)


class DpiaIn(Links):
    title: str = Field(max_length=240)
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
    supervisory_authority_consulted: bool = False
    data_subjects_consulted: bool = False
    outcome: DpiaOutcome
    assessed_by: str = Field(max_length=120)
    assessment_date: date
    review_date: date


class BiaIn(Links):
    process_name: str = Field(max_length=240)
    process_description: str
    owner_role: str = Field(max_length=120)
    rto_hours: float = Field(ge=0)
    rpo_hours: float = Field(ge=0)
    mtpd_hours: float = Field(gt=0)
    currency: str = Field(min_length=1, max_length=8)
    impact_1h: float = Field(ge=0)
    impact_24h: float = Field(ge=0)
    impact_1w: float = Field(ge=0)
    impact_note: str
    workaround: str
    recovery_note: str | None = None


class RevisionIn(BaseModel):
    kind: Literal["ASSET", "ROPA", "DPIA", "BIA"]
    record_ref: str = Field(min_length=1, max_length=24)
    expected_revision: int = Field(ge=0)
    owner: str = Field(min_length=1, max_length=160)
    review_date: date
    change_note: str
    content: dict


class CoverageIn(BaseModel):
    control_ref: str
    evidence_ref: str
    source_system: str
    owner: str = Field(min_length=1, max_length=160)
    period_start: date
    period_end: date
    review_date: date
    coverage_note: str


class ExerciseIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    bia_ref: str
    performed_on: date
    recovery_hours: float = Field(ge=0)
    data_loss_hours: float = Field(ge=0)
    evidence_ref: str
    note: str
    follow_up: str
