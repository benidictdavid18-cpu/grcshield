from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field
class ReleaseIn(BaseModel):
    version: str=Field(min_length=1,max_length=32)
    change_note: str=Field(min_length=1)
class ReleaseApprovalIn(BaseModel):
    note: str=Field(min_length=1)
    acknowledge_evidence_limitations: bool=False
class ReleaseOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    version: str
    status: str
    entries: list[dict]
    entry_count: int
    content_digest: str
    change_note: str
    prepared_by: str
    evidence_warnings: list[str]
    evidence_limitations_acknowledged: bool
    approved_by: str | None
    approved_at: datetime | None
    approval_note: str | None
    disclaimer: str="Sample / Portfolio Assessment"
