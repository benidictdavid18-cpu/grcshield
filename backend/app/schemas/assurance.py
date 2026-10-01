from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.control_testing import FindingSource


class ProgrammeIn(BaseModel):
    owner: str = Field(min_length=1, max_length=160)
    risk_basis: str = Field(min_length=1)
    coverage: str = Field(min_length=1)
    frequency: str = Field(min_length=1)
    methods: str = Field(min_length=1)
    reporting: str = Field(min_length=1)
    starts_on: date
    ends_on: date
    review_date: date
    expected_revision: int | None = None


class ProgrammeOut(ProgrammeIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    programme_ref: str
    revision: int


class AuditIn(BaseModel):
    programme_ref: str
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
    outcome_summary: str | None = None
    expected_revision: int | None = None


class ReviewIn(BaseModel):
    review_date: date
    chair: str
    attendees: str
    inputs_considered: str
    decisions: str
    actions: str
    next_review_date: date
    expected_revision: int | None = None


class InputIn(BaseModel):
    consideration: str
    evidence_ref: str | None = None
    no_evidence_reason: str | None = None


class ActionIn(BaseModel):
    action_ref: str = Field(min_length=1, max_length=32)
    description: str
    owner: str = Field(max_length=160)
    due_date: date
    finding_ref: str | None = None


class CompletionIn(BaseModel):
    completed_on: date
    evidence_ref: str
    note: str


class NonconformityIn(BaseModel):
    description: str
    source: FindingSource
    identified_date: date
    identified_by: str = Field(max_length=120)
    owner: str = Field(max_length=120)
    immediate_correction: str
    root_cause_analysis: str | None = None
    corrective_action: str | None = None
    target_date: date | None = None
    finding_ref: str | None = None


class VerificationIn(BaseModel):
    checked_on: date
    result: Literal["EFFECTIVE", "INEFFECTIVE"]
    note: str
    evidence_ref: str


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cycle_ref: str
    kind: str
    audit_id: int | None
    review_id: int | None
    programme_id: int | None
    status: str
    revision: int
    completed_on: date | None
    completed_by: str | None
    evidence_id: int | None
    completion_snapshot: dict | None


class InputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    consideration: str
    evidence_id: int | None
    no_evidence_reason: str | None


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action_ref: str
    cycle_id: int
    description: str
    owner: str
    due_date: date
    finding_id: int | None
    status: str
    evidence_id: int | None
    completed_on: date | None
    completed_by: str | None
    completion_note: str | None


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    checked_on: date
    result: str
    note: str
    evidence_id: int
    actor: str
    snapshot: dict
