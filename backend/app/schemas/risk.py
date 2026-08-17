from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.risk_scoring import (
    ControlEffectivenessBasis,
    RiskBand,
    RiskCategory,
    RiskStatus,
    TreatmentDecision,
)


class AppetiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: RiskCategory
    category_label: str
    max_acceptable_band: RiskBand
    approver_role: str
    rationale: str
    last_reviewed: date | None = None


class LinkedControlOut(BaseModel):
    control_id: str
    title: str
    control_family: str
    owner_role: str
    annex_a_refs: list[str]
    effectiveness_basis: ControlEffectivenessBasis
    credits_reduction: bool
    note: str | None = None


class ScoreOut(BaseModel):
    likelihood: int
    impact: int
    score: int
    band: RiskBand


class AppetiteComparisonOut(BaseModel):
    """None-valued fields mean 'no appetite is defined', not 'within appetite'."""

    max_acceptable_band: RiskBand | None = None
    approver_role: str | None = None
    exceeds_appetite: bool | None = None


class RiskSummaryOut(BaseModel):
    risk_ref: str
    title: str
    category: RiskCategory
    category_label: str
    owner_role: str
    status: RiskStatus
    treatment_decision: TreatmentDecision
    inherent: ScoreOut
    residual: ScoreOut
    appetite: AppetiteComparisonOut
    justification_outstanding: bool
    has_uncredited_controls: bool


class RiskDetailOut(RiskSummaryOut):
    description: str
    asset: str
    threat: str
    vulnerability: str
    residual_justification: str
    treatment_summary: str
    date_identified: date
    last_reviewed: date | None = None
    next_review: date | None = None
    controls: list[LinkedControlOut]


class ResidualUpdateIn(BaseModel):
    """Payload for re-scoring residual risk.

    Likelihood and impact are supplied directly. There is deliberately no
    'control effectiveness percentage' field to derive them from.
    """

    residual_likelihood: int = Field(ge=1, le=5)
    residual_impact: int = Field(ge=1, le=5)
    residual_justification: str

    @field_validator("residual_justification")
    @classmethod
    def justification_must_say_something(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "residual_justification is required: state which control reduced which "
                "dimension (likelihood or impact) and why the other did not move."
            )
        return value


class BandBoundaryOut(BaseModel):
    band: str
    min_score: int
    max_score: int


class RegisterSummaryOut(BaseModel):
    total: int
    by_residual_band: dict[str, int]
    exceeding_appetite: int
    justifications_outstanding: int
    bands: list[BandBoundaryOut]
