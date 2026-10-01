from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanIn(BaseModel):
    risk_ref: str
    title: str=Field(min_length=1,max_length=240)
    owner: str=Field(min_length=1,max_length=160)
    resources: str=Field(min_length=1)
    rationale: str=Field(min_length=1)
    control_refs: list[str]=Field(min_length=1)
    expected_revision: int | None=Field(default=None,ge=1)
class MilestoneIn(BaseModel):
    title: str=Field(min_length=1,max_length=240)
    owner: str=Field(min_length=1,max_length=160)
    due_date: date
    dependency_ref: str | None=None
    remediation_ref: str | None=None
class CompletionIn(BaseModel):
    evidence_ref: str
    note: str=Field(min_length=1)
class MilestoneOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    milestone_ref: str
    title: str
    owner: str
    due_date: date
    status: str
    dependency_id: int | None
    remediation_id: int | None
    evidence_id: int | None
    completion_note: str | None
    completed_on: date | None
    completed_by: str | None
    disclaimer: str="Sample / Portfolio Assessment"
class PlanOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    plan_ref: str
    risk_id: int
    title: str
    owner: str
    resources: str
    rationale: str
    review_deadline: date
    status: str
    revision: int
    approved_by: str | None
    approved_at: datetime | None
    approved_snapshot: dict | None
    approval_note: str | None
    verification_evidence_id: int | None
    verification_note: str | None
    closed_by: str | None
    controls: list[str]=[]
    milestones: list[MilestoneOut]=[]
    disclaimer: str="Sample / Portfolio Assessment"
