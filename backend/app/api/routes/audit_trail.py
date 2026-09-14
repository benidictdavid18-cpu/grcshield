"""Reading the audit trail.

List and filter only. There is no endpoint that edits or removes an event, and the
router is mounted behind ``require_write`` like every other register, which for a GET
means any authenticated user -- the read-only auditor role can read the trail, which is
who it is for.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit_trail import AuditEvent
from app.schemas.audit_trail import AuditEventOut

router = APIRouter(prefix="/audit-events", tags=["audit trail"])


def _out(event: AuditEvent) -> AuditEventOut:
    return AuditEventOut(
        id=event.id,
        occurred_at=event.created_at,
        actor_username=event.actor_username,
        actor_role=event.actor_role,
        action=event.action,
        record_type=event.record_type,
        record_ref=event.record_ref,
        before=event.before,
        after=event.after,
        summary=event.summary,
    )


@router.get("", response_model=list[AuditEventOut])
def list_events(
    record_ref: str | None = Query(default=None, description="RISK-004, A.8.5, TEST-013 ..."),
    record_type: str | None = Query(default=None),
    actor: str | None = Query(default=None, description="Username"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AuditEventOut]:
    """Most recent first. Filters combine."""
    query = select(AuditEvent)
    if record_ref:
        query = query.where(AuditEvent.record_ref == record_ref.upper())
    if record_type:
        query = query.where(AuditEvent.record_type == record_type.upper())
    if actor:
        query = query.where(AuditEvent.actor_username == actor.strip().lower())
    query = query.order_by(AuditEvent.id.desc()).limit(limit)
    return [_out(e) for e in db.scalars(query).all()]
