"""A durable in-app outbox. No external recipient or delivery is inferred."""

import hashlib
from datetime import timedelta

from sqlalchemy import select

from app.core import clock
from app.models.context import ContextEntry
from app.models.document import ControlledDocument
from app.models.monitoring import MeasurementPlan, MonitoringObservation
from app.models.notifications import Notification, NotificationRouting
from app.models.privacy import RiskException
from app.models.risk import Risk
from app.models.soa import Evidence, RemediationItem
from app.models.suppliers import Supplier
from app.models.user import User
from app.services.provenance import ProofError


def candidates(db):
    for row in db.scalars(select(Risk)):
        if row.next_review:
            yield "RISK_REVIEW", row.risk_ref, row.owner_role, row.next_review
    for row in db.scalars(select(RiskException)):
        if row.status.value not in ("REJECTED", "WITHDRAWN"):
            yield "ACCEPTANCE_EXPIRY", row.exception_ref, row.approver_role, row.expiry_date
    for row in db.scalars(select(RemediationItem)):
        if row.is_open:
            yield "REMEDIATION_DUE", row.remediation_ref, row.owner, row.due_date
    for model, key, date_field, owner_field, kind in [
        (Supplier, "supplier_ref", "review_date", "owner", "SUPPLIER_REVIEW"),
        (ContextEntry, "context_ref", "review_date", "owner", "CONTEXT_REVIEW"),
        (ControlledDocument, "document_ref", "review_date", "owner", "DOCUMENT_REVIEW"),
    ]:
        for row in db.scalars(select(model)):
            yield kind, getattr(row, key), getattr(row, owner_field), getattr(row, date_field)
    for row in db.scalars(select(Evidence)):
        yield "EVIDENCE_EXPIRY", row.evidence_ref, row.collected_by, row.valid_until
    for row in db.scalars(select(MeasurementPlan)):
        yield "MEASUREMENT_DUE", str(row.id), row.collection_owner, row.next_collection
    for row in db.scalars(
        select(MonitoringObservation).where(
            MonitoringObservation.band == "RED", MonitoringObservation.evaluated_on.is_(None)
        )
    ):
        yield (
            "KRI_BREACH",
            str(row.id),
            row.definition_snapshot["plan"]["evaluation_owner"],
            row.period_end,
        )


def run(db):
    today = clock.today()
    made = 0
    for kind, ref, owner, due in candidates(db):
        if due > today + timedelta(days=7):
            continue
        key = hashlib.sha256(f"{kind}:{ref}:{due}".encode()).hexdigest()
        if db.scalar(select(Notification.id).where(Notification.dedup_key == key)) is None:
            db.add(
                Notification(
                    dedup_key=key,
                    record_ref=ref,
                    kind=kind,
                    owner=owner,
                    due_date=due,
                    message=f'Sample / Portfolio Assessment: {ref} requires {kind.lower().replace("_"," ")} by {due}.',
                )
            )
            made += 1
    db.flush()
    for row in db.scalars(
        select(Notification).where(Notification.status != "ACKNOWLEDGED").with_for_update()
    ):
        overdue = today > row.due_date + timedelta(days=7)
        if overdue and row.escalated_on is None:
            row.escalated_on = today
        route = db.scalar(
            select(NotificationRouting).where(
                NotificationRouting.owner == ("ISMS escalation" if overdue else row.owner)
            )
        )
        if route is None and overdue:
            route = db.scalar(
                select(NotificationRouting).where(NotificationRouting.owner == row.owner)
            )
        user = db.get(User, route.user_id) if route else None
        if row.status == "DELIVERED" and user and row.user_id == user.id and user.is_active:
            continue
        row.attempts += 1
        if not user or not user.is_active:
            row.status, row.last_error = (
                "PENDING",
                "No active authorized recipient mapping. Assign ownership in notification routing.",
            )
            continue
        row.user_id, row.status, row.delivered_on, row.last_error = (
            user.id,
            "DELIVERED",
            today,
            None,
        )
    return {"created": made, "channel": "IN_APP"}


def acknowledge(db, row, actor):
    if row.user_id != actor.id:
        raise PermissionError("Only the assigned recipient can acknowledge this reminder.")
    if row.status != "DELIVERED":
        raise ProofError("status", "Only a delivered reminder can be acknowledged.")
    row.status, row.acknowledged_on, row.acknowledged_by = (
        "ACKNOWLEDGED",
        clock.today(),
        actor.username,
    )


def route(db, payload, actor):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not user.is_active or not user.can_write:
        raise ProofError("username", "Choose an active maintainer account.")
    if not payload.owner.strip() or "TODO AUTHOR:BENNY" in payload.owner:
        raise ProofError("owner", "Use an authored accountable owner label.")
    row = db.scalar(
        select(NotificationRouting)
        .where(NotificationRouting.owner == payload.owner)
        .with_for_update()
    )
    if row is None:
        row = NotificationRouting(owner=payload.owner)
        db.add(row)
    row.user_id, row.assigned_by = user.id, actor.username
    return row
