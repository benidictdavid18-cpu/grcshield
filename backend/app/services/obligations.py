from sqlalchemy import select

from app.core import clock
from app.models.audit_trail import AuditAction
from app.models.obligations import Obligation, ObligationDecision
from app.models.risk import Control
from app.models.soa import Evidence, RemediationItem
from app.models.suppliers import Supplier
from app.services import acceptance, audit_trail
from app.services.assurance import required, snapshot
from app.services.people import reference
from app.services.planning import lookup
from app.services.provenance import ProofError


def record(db, row, before, after, actor):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.OBLIGATION_CHANGED,
        record_type="OBLIGATION",
        record_ref=row.obligation_ref,
        before=before,
        after=after,
        summary="Obligation decision retained with source and accountable author; no automated legal conclusion.",
    )


def save(db, ref, payload, actor):
    reference(ref)
    row = db.scalar(select(Obligation).where(Obligation.obligation_ref == ref).with_for_update())
    if row and row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the current obligation.")
    for field in ("title", "source", "source_version", "jurisdiction", "requirement", "owner"):
        if not getattr(payload, field).strip():
            raise ProofError(field, "Record the source value or an explicit author task.")
    control = lookup(db, Control, Control.control_id, payload.control_ref, "control_ref")
    supplier = lookup(db, Supplier, Supplier.supplier_ref, payload.supplier_ref, "supplier_ref")
    before = snapshot(row) if row else None
    if row is None:
        row = Obligation(obligation_ref=ref, revision=0)
        db.add(row)
    for field, value in payload.model_dump(
        exclude={"control_ref", "supplier_ref", "expected_revision"}
    ).items():
        setattr(row, field, value)
    row.control_id, row.supplier_id = control.id, supplier.id if supplier else None
    row.applicability, row.rationale, row.approved_by, row.approved_on = (
        "UNASSESSED",
        None,
        None,
        None,
    )
    row.revision += 1
    record(db, row, before, snapshot(row), actor)
    return row


def decide(db, row, payload, actor):
    if row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Decide on the current obligation revision.")
    required(
        [payload.note, row.source, row.source_version, row.jurisdiction, row.requirement, row.owner]
    )
    if payload.decided_on > clock.today():
        raise ProofError("decided_on", "Decision dates cannot be in the future.")
    latest = db.scalar(
        select(ObligationDecision)
        .where(ObligationDecision.obligation_id == row.id)
        .order_by(ObligationDecision.id.desc())
    )
    if latest and payload.decided_on < latest.decided_on:
        raise ProofError("decided_on", "A decision cannot precede the latest retained decision.")
    before = snapshot(row)
    remediation = lookup(
        db,
        RemediationItem,
        RemediationItem.remediation_ref,
        payload.remediation_ref,
        "remediation_ref",
    )
    if payload.kind == "APPLICABILITY":
        if not acceptance.authority(db, actor, "Head of Legal & Compliance"):
            raise PermissionError(
                "Current Head of Legal & Compliance authority is required to approve applicability."
            )
        if payload.result not in ("APPLICABLE", "NOT_APPLICABLE"):
            raise ProofError("result", "Choose an applicability decision.")
        row.applicability, row.rationale = payload.result, payload.note
        row.approved_by, row.approved_on = actor.username, payload.decided_on
    else:
        if row.applicability != "APPLICABLE" or payload.result not in (
            "SATISFIED",
            "ACTION_REQUIRED",
        ):
            raise ProofError("result", "Evaluate an approved applicable obligation.")
        if payload.result == "ACTION_REQUIRED" and (
            remediation is None
            or not remediation.owner
            or remediation.due_date is None
            or str(remediation.status.value) in ("COMPLETED", "CANCELLED")
        ):
            raise ProofError(
                "remediation_ref", "Link an open remediation with an owner and due date."
            )
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    row.revision += 1
    item = ObligationDecision(
        obligation_id=row.id,
        actor=actor.username,
        evidence_id=evidence.id,
        remediation_id=remediation.id if remediation else None,
        snapshot=snapshot(row),
        **payload.model_dump(exclude={"expected_revision", "evidence_ref", "remediation_ref"}),
    )
    db.add(item)
    record(db, row, before, {"obligation": snapshot(row), "decision": snapshot(item)}, actor)
    return item
