from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PlanIn(BaseModel):
    method: str
    population: str
    source: str
    collection_owner: str = Field(max_length=160)
    evaluation_owner: str = Field(max_length=160)
    frequency: str = Field(max_length=80)
    next_collection: date
    expected_revision: int | None = None


class ObservationIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    expected_revision: int
    period_start: date
    period_end: date
    value: float | None
    source_query: str
    population: str
    evidence_ref: str


class EvaluationIn(BaseModel):
    evaluated_on: date
    note: str
    remediation_ref: str | None = None
