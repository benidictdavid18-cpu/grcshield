from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    service: str = Field(min_length=1)
    owner: str = Field(min_length=1, max_length=160)
    criticality: Literal["UNASSESSED", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = "UNASSESSED"
    information_access: str
    agreement_terms: str
    shared_responsibility: str
    exit_plan: str
    review_date: date
    control_ref: str
    dependency_ref: str | None = None
    agreement_attachment_id: int | None = None
    expected_revision: int | None = None


class ReviewIn(BaseModel):
    expected_revision: int
    reviewed_on: date
    next_review: date
    result: Literal["ACCEPTABLE", "ACTION_REQUIRED", "EXIT"]
    note: str
    evidence_ref: str
    action: str | None = None
    action_owner: str | None = Field(default=None, max_length=160)
    action_due: date | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_ref: str
    name: str
    service: str
    owner: str
    criticality: str
    information_access: str
    agreement_terms: str
    shared_responsibility: str
    exit_plan: str
    review_date: date
    control_id: int
    dependency_id: int | None
    agreement_attachment_id: int | None
    status: str
    reviewed_on: date | None
    revision: int
    disclaimer: str = "Sample / Portfolio Assessment"
