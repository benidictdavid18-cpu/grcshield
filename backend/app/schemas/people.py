from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RequirementIn(BaseModel):
    role: str = Field(min_length=1, max_length=160)
    requirement: str
    evaluation_method: str
    owner: str = Field(min_length=1, max_length=160)
    review_date: date
    expected_revision: int | None = None


class EvaluationIn(BaseModel):
    expected_revision: int
    subject_ref: str = Field(min_length=1, max_length=64)
    evaluated_on: date
    review_date: date
    result: Literal["DEVELOPMENT_REQUIRED", "COMPETENT"]
    evidence_ref: str
    demonstrated_outcome: str
    development_action: str | None = None
    action_due: date | None = None


class CommunicationIn(BaseModel):
    topic: str
    audience: str
    owner: str = Field(min_length=1, max_length=160)
    method: str
    planned_on: date
    document_revision_id: int | None = None
