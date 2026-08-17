from pydantic import BaseModel, ConfigDict

from app.models.framework import MappingRelationship, ScopeStatus


class MappedCriterion(BaseModel):
    """A SOC 2 criterion reached from an ISO control."""

    model_config = ConfigDict(from_attributes=True)

    control_ref: str
    title: str
    group_ref: str
    group_title: str
    relationship_type: MappingRelationship


class ControlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    control_ref: str
    title: str
    group_ref: str
    group_title: str
    in_scope: bool
    scope_note: str | None = None


class ControlDetailOut(ControlOut):
    framework_code: str
    mappings: list[MappedCriterion] = []


class GroupSummary(BaseModel):
    group_ref: str
    group_title: str
    total: int
    in_scope: int
    out_of_scope: int


class FrameworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    version: str
    publisher: str
    scope_status: ScopeStatus
    scope_note: str
    control_count: int


class FrameworkDetailOut(FrameworkOut):
    groups: list[GroupSummary] = []
