from datetime import date
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class DocumentIn(BaseModel):
    title: str=Field(min_length=1,max_length=240)
    owner: str=Field(min_length=1,max_length=160)
    classification: Literal["PUBLIC","INTERNAL","CONFIDENTIAL","RESTRICTED"]="INTERNAL"
    source_kind: Literal["INTERNAL","EXTERNAL"]="INTERNAL"
    external_source: str | None=None
    distribution: str=Field(min_length=1)
    review_date: date

class DocumentOut(DocumentIn):
    model_config=ConfigDict(from_attributes=True)
    id: int
    document_ref: str
    disclaimer: str="Sample / Portfolio Assessment"

class RevisionIn(BaseModel):
    version: str=Field(min_length=1,max_length=32)
    content: str=Field(min_length=1,max_length=1000000)
    change_note: str=Field(min_length=1)
    evidence_ref: str | None=None

class RevisionOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    document_id: int
    version: str
    content: str
    content_digest: str
    change_note: str
    author: str
    status: str
    evidence_id: int | None
    approved_by: str | None
    approved_on: date | None
    approval_note: str | None
    published_on: date | None
    withdrawal_note: str | None
    disclaimer: str="Sample / Portfolio Assessment"
