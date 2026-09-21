from datetime import date
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class AttachmentIn(BaseModel):
    version: str=Field(min_length=1,max_length=32)
    filename: str=Field(min_length=1,max_length=240)
    content_type: Literal["application/pdf","image/png","image/jpeg","text/plain","text/csv","application/json"]
    content_base64: str=Field(min_length=1,max_length=11184812)
    source: str=Field(min_length=1,max_length=4000)
    access_scope: Literal["REGISTER_READERS","MAINTAINERS"]="REGISTER_READERS"
    retention_until: date
    retention_reason: str=Field(min_length=1,max_length=4000)
    legal_hold: bool=False

class AttachmentOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    evidence_id: int
    version: str
    filename: str
    content_type: str
    byte_size: int
    sha256: str
    source: str
    uploaded_by: str
    uploaded_on: date
    access_scope: str
    retention_until: date
    retention_reason: str
    legal_hold: bool
    purged_on: date | None
    purged_by: str | None
    purge_reason: str | None
    disclaimer: str="Sample / Portfolio Assessment"

class RetentionIn(BaseModel):
    retention_until: date
    legal_hold: bool
    reason: str=Field(min_length=1)
