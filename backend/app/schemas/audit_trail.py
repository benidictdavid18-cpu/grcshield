from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: int
    occurred_at: datetime
    actor_username: str
    actor_role: str
    action: str
    record_type: str
    record_ref: str
    before: dict[str, Any] | None
    after: dict[str, Any]
    summary: str
