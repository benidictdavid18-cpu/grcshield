from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1)
    source: str = Field(min_length=1)
    occurred_on: date
    reported_on: date
    owner: str = Field(min_length=1, max_length=160)
    risk_ref: str
    control_ref: str
    finding_ref: str | None = None


class EntryIn(BaseModel):
    kind: Literal[
        "TRIAGE",
        "RESPONSE",
        "COMMUNICATION",
        "EVIDENCE",
        "CONTAINED",
        "RECOVERED",
        "CLOSED",
        "REOPENED",
    ]
    occurred_on: date
    note: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    disposition: Literal["DISMISSED", "INCIDENT"] | None = None
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    notification_decision: str | None = None
    evidence_ref: str | None = None
    attachment_id: int | None = None
    custody_note: str | None = None
    lessons: str | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=160)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_ref: str
    title: str
    description: str
    source: str
    occurred_on: date
    reported_on: date
    reporter: str
    owner: str
    risk_id: int
    control_id: int
    finding_id: int | None
    status: str
    severity: str
    classification_note: str
    notification_decision: str
    lessons: str
    closure_note: str
    closed_on: date | None
    evidence_id: int | None
    revision: int
    disclaimer: str = "Sample / Portfolio Assessment"


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    occurred_on: date
    actor: str
    note: str
    attachment_id: int | None
    custody_note: str | None
    snapshot: dict
    disclaimer: str = "Sample / Portfolio Assessment"
