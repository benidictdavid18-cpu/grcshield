from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class AuthorityIn(BaseModel):
    username: str
    business_role: str = Field(min_length=1,max_length=120)
    expires_on: date
    grant_reason: str = Field(min_length=1)
class DecisionIn(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "WITHDRAWN"]
    note: str = Field(min_length=1)
    expiry_date: date | None = None
