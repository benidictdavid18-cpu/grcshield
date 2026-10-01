from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextIn(BaseModel):
    kind: Literal["ISSUE", "PARTY_REQUIREMENT", "PROCESS"]
    topic: str = Field(default="GENERAL",min_length=1,max_length=64)
    title: str = Field(min_length=1,max_length=240)
    statement: str = Field(min_length=1)
    source: str = Field(min_length=1)
    owner: str = Field(min_length=1,max_length=160)
    review_date: date
    relevance: Literal["UNASSESSED", "RELEVANT", "NOT_RELEVANT"] = "UNASSESSED"
    decision_note: str = Field(min_length=1)
    risk_ref: str | None = None
    expected_revision: int | None = Field(default=None,ge=1)

class ContextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    context_ref: str
    kind: str
    topic: str
    title: str
    statement: str
    source: str
    owner: str
    review_date: date
    relevance: str
    decision_note: str
    risk_id: int | None
    revision: int
    status: str
    reviewed_by: str | None
    reviewed_on: date | None
    disclaimer: str = "Sample / Portfolio Assessment"

class ScopeIn(BaseModel):
    version: str = Field(min_length=1,max_length=32)
    statement: str = Field(min_length=1)
    interfaces: str = Field(min_length=1)
    exclusions: str = Field(min_length=1)
    owner: str = Field(min_length=1,max_length=160)
    review_date: date
    context_refs: list[str] = Field(min_length=1)

class ApprovalIn(BaseModel):
    note: str = Field(min_length=1)

class ScopeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: str
    statement: str
    interfaces: str
    exclusions: str
    owner: str
    review_date: date
    context_snapshot: list[dict]
    status: str
    approved_by: str | None
    approved_on: date | None
    approval_note: str | None
    disclaimer: str = "Sample / Portfolio Assessment"
