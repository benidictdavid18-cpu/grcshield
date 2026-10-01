from pydantic import BaseModel, ConfigDict, Field


class ProofIn(BaseModel):
    test_ref: str
    note: str = Field(min_length=1)

class DispositionIn(BaseModel):
    replacement_ref: str | None = None
    reason: str = Field(min_length=1)

class ResolutionIn(BaseModel):
    evidence_ref: str
    resolution: str = Field(min_length=1)

class ReassessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trigger_test_id: int
    record_type: str
    record_ref: str
    owner: str
    reason: str
    status: str
    resolution: str | None
    evidence_id: int | None
    resolved_by: str | None
    disclaimer: str = "Sample / Portfolio Assessment"
