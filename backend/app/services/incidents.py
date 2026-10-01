"""Event classification is an attributable judgment, never inferred from a finding."""

import hashlib

from sqlalchemy import select

from app.core import clock
from app.models.attachment import EvidenceAttachment
from app.models.audit import AuditFinding
from app.models.audit_trail import AuditAction
from app.models.incidents import IncidentEntry, SecurityEvent
from app.models.risk import Control, Risk, RiskControl
from app.models.soa import Evidence
from app.services import audit_trail
from app.services.assurance import required, snapshot
from app.services.planning import lookup
from app.services.provenance import ProofError


def record(db, row, before, actor):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.INCIDENT_CHANGED,
        record_type="SECURITY_EVENT",
        record_ref=row.event_ref,
        before=before,
        after=snapshot(row),
        summary="Security event decision retained; no automatic risk or breach judgment.",
    )


def create(db, ref, payload, actor):
    if not ref.strip() or len(ref) > 32:
        raise ProofError("event_ref", "Use a nonblank reference of at most 32 characters.")
    if db.scalar(select(SecurityEvent.id).where(SecurityEvent.event_ref == ref)):
        raise ProofError(
            "event_ref", "This event exists; append a timeline entry instead of overwriting it."
        )
    if not payload.occurred_on <= payload.reported_on <= clock.today():
        raise ProofError(
            "reported_on", "Use actual occurrence and report dates in chronological order."
        )
    for field in ("title", "description", "source", "owner"):
        if not getattr(payload, field).strip():
            raise ProofError(field, "This field cannot be blank.")
    risk = lookup(db, Risk, Risk.risk_ref, payload.risk_ref, "risk_ref")
    control = lookup(db, Control, Control.control_id, payload.control_ref, "control_ref")
    if (
        db.scalar(
            select(RiskControl).where(
                RiskControl.risk_id == risk.id, RiskControl.control_id == control.id
            )
        )
        is None
    ):
        raise ProofError("control_ref", "Choose a control linked to this risk.")
    finding = lookup(db, AuditFinding, AuditFinding.finding_ref, payload.finding_ref, "finding_ref")
    if finding and finding.control_id != control.id:
        raise ProofError("finding_ref", "The finding must concern the linked control.")
    row = SecurityEvent(
        event_ref=ref,
        reporter=actor.username,
        risk_id=risk.id,
        control_id=control.id,
        finding_id=finding.id if finding else None,
        **payload.model_dump(exclude={"risk_ref", "control_ref", "finding_ref"}),
    )
    db.add(row)
    db.flush()
    record(db, row, None, actor)
    return row


def append(db, row, payload, actor):
    if row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the event before recording this decision.")
    required([payload.note], "note")
    if not row.reported_on <= payload.occurred_on <= clock.today():
        raise ProofError("occurred_on", "Response entries must fall between reporting and today.")
    last = db.scalar(
        select(IncidentEntry)
        .where(IncidentEntry.event_id == row.id)
        .order_by(IncidentEntry.id.desc())
    )
    if last and payload.occurred_on < last.occurred_on:
        raise ProofError(
            "occurred_on", "A new entry cannot predate the latest retained response decision."
        )
    before = snapshot(row)
    if row.status in ("CLOSED", "DISMISSED") and payload.kind != "REOPENED":
        raise ProofError(
            "status", "Reopen the event with a reason before adding response decisions."
        )
    attachment = None
    if payload.kind == "TRIAGE":
        if row.status != "REPORTED" or payload.disposition is None:
            raise ProofError("disposition", "Triage a reported event as DISMISSED or INCIDENT.")
        required([payload.owner or row.owner], "owner")
        row.owner = payload.owner or row.owner
        if payload.disposition == "INCIDENT" and payload.severity is None:
            raise ProofError("severity", "An incident requires an authored severity decision.")
        required([payload.notification_decision or ""], "notification_decision")
        row.status = payload.disposition
        row.severity = payload.severity or "UNASSESSED"
        row.classification_note = payload.note
        row.notification_decision = payload.notification_decision
    elif payload.kind == "REOPENED":
        if row.status not in ("CLOSED", "DISMISSED"):
            raise ProofError("status", "Only a closed or dismissed event can be reopened.")
        row.status, row.closed_on = "REPORTED", None
    elif payload.kind in ("CONTAINED", "RECOVERED", "CLOSED"):
        predecessor = {"CONTAINED": "INCIDENT", "RECOVERED": "CONTAINED", "CLOSED": "RECOVERED"}
        if row.status != predecessor[payload.kind]:
            raise ProofError("status", "Record triage, containment, recovery and closure in order.")
        if payload.kind == "CLOSED":
            required([payload.lessons or "", row.notification_decision], "lessons")
            if not payload.evidence_ref:
                raise ProofError("evidence_ref", "Closure needs a real evidence reference.")
            evidence = lookup(
                db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref"
            )
            row.evidence_id, row.lessons, row.closure_note = (
                evidence.id,
                payload.lessons,
                payload.note,
            )
            row.closed_on = payload.occurred_on
        row.status = payload.kind
    elif payload.kind == "EVIDENCE":
        required([payload.custody_note or ""], "custody_note")
        attachment = (
            db.get(EvidenceAttachment, payload.attachment_id) if payload.attachment_id else None
        )
        if attachment is None or attachment.purged_on is not None:
            raise ProofError(
                "attachment_id", "Custody requires an existing retained source attachment."
            )
        if hashlib.sha256(attachment.content_data).hexdigest() != attachment.sha256:
            raise ProofError("attachment_id", "Attachment integrity verification failed.")
    elif payload.kind == "COMMUNICATION":
        required([payload.notification_decision or ""], "notification_decision")
        row.notification_decision = payload.notification_decision
    row.revision += 1
    entry = IncidentEntry(
        event_id=row.id,
        kind=payload.kind,
        occurred_on=payload.occurred_on,
        actor=actor.username,
        note=payload.note,
        attachment_id=attachment.id if attachment else None,
        custody_note=payload.custody_note,
        snapshot=snapshot(row),
    )
    if attachment:
        entry.snapshot["attachment"] = {
            "id": attachment.id,
            "sha256": attachment.sha256,
            "version": attachment.version,
        }
    db.add(entry)
    record(db, row, before, actor)
    return entry
