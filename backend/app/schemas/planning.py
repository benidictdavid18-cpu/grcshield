from datetime import date,datetime
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,FiniteFloat
class ISMSPlanIn(BaseModel):
    kind: Literal["OBJECTIVE","CHANGE"]
    title: str=Field(min_length=1,max_length=240)
    owner: str=Field(min_length=1,max_length=160)
    resources: str=Field(min_length=1)
    rationale: str=Field(min_length=1)
    context_ref: str
    risk_ref: str | None=None
    kri_ref: str | None=None
    due_date: date | None=None
    measure_definition: str | None=None
    target_value: FiniteFloat | None=None
    direction: Literal["HIGHER_IS_BETTER","LOWER_IS_BETTER"] | None=None
    impact_assessment: str | None=None
    rollback_plan: str | None=None
    expected_revision: int | None=Field(default=None,ge=1)
class ISMSPlanOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    plan_ref: str
    kind: str
    title: str
    owner: str
    resources: str
    rationale: str
    context_id: int
    risk_id: int | None
    kri_id: int | None
    due_date: date | None
    measure_definition: str | None
    target_value: float | None
    direction: str | None
    impact_assessment: str | None
    rollback_plan: str | None
    status: str
    revision: int
    approved_by: str | None
    approved_at: datetime | None
    approved_snapshot: dict | None
    approval_note: str | None
    implementation_date: date | None
    implementation_evidence_id: int | None
    implementation_note: str | None
    cancellation_note: str | None
    disclaimer: str="Sample / Portfolio Assessment"
class EvaluationIn(BaseModel):
    observed_on: date
    observed_value: FiniteFloat | None=None
    evidence_ref: str
    evaluation_note: str=Field(min_length=1)
class ImplementationIn(BaseModel):
    implemented_on: date
    evidence_ref: str
    note: str=Field(min_length=1)
class EvaluationOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    observed_on: date
    observed_value: float | None
    evaluation_note: str
    evidence_id: int
    actor: str
    disclaimer: str="Sample / Portfolio Assessment"
