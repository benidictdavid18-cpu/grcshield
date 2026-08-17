from pydantic import BaseModel


class ReportOut(BaseModel):
    code: str
    title: str
    audience: str
    decision_supported: str
    available_from_phase: int
    implemented: bool
    endpoint: str | None = None
