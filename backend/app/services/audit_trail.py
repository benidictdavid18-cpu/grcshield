"""Writing the audit trail.

One function, ``record_change``, called from each write endpoint after validation has
passed and before the route commits. It adds the event to the session and returns it;
it does not commit, so the event and the change it describes land in the same
transaction or not at all.

The snapshot helpers turn model attributes into something JSON can hold. Enums become
their value and dates their ISO string, so a ``before`` written today reads the same as
an ``after`` written next year.
"""

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_trail import AuditAction, AuditEvent
from app.models.user import User


def jsonable(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(v) for v in value]
    return value


def snapshot(record: object, fields: tuple[str, ...]) -> dict[str, Any]:
    """The named attributes of a model instance, JSON-ready."""
    return {field: jsonable(getattr(record, field)) for field in fields}


def record_change(
    db: Session,
    *,
    actor: User,
    action: AuditAction,
    record_type: str,
    record_ref: str,
    before: dict[str, Any] | None,
    after: dict[str, Any],
    summary: str,
) -> AuditEvent:
    event = AuditEvent(
        actor_username=actor.username,
        actor_role=actor.role.value,
        action=action.value,
        record_type=record_type,
        record_ref=record_ref,
        before=jsonable(before) if before is not None else None,
        after=jsonable(after),
        summary=summary,
    )
    db.add(event)
    return event


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Which keys differ, for a summary that names them."""
    return [key for key in after if before.get(key) != after.get(key)]
