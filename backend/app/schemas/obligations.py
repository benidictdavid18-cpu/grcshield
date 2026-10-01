from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ObligationIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    kind: Literal["LEGAL", "REGULATORY", "CONTRACTUAL"]
    source: str
    source_version: str = Field(min_length=1, max_length=160)
    jurisdiction: str = Field(min_length=1, max_length=160)
    requirement: str
    owner: str = Field(min_length=1, max_length=160)
    review_date: date
    control_ref: str
    supplier_ref: str | None = None
    expected_revision: int | None = None


class DecisionIn(BaseModel):
    expected_revision: int
    kind: Literal["APPLICABILITY", "EVALUATION"]
    decided_on: date
    result: Literal["APPLICABLE", "NOT_APPLICABLE", "SATISFIED", "ACTION_REQUIRED"]
    note: str
    evidence_ref: str
    remediation_ref: str | None = None
