from sqlalchemy import select

from app.core import clock
from app.models.attachment import EvidenceAttachment
from app.models.audit_trail import AuditAction
from app.models.risk import Control
from app.models.soa import Evidence
from app.models.suppliers import Supplier, SupplierReview
from app.services import audit_trail
from app.services.assurance import required, snapshot
from app.services.planning import lookup
from app.services.provenance import ProofError


def record(db, ref, before, after, actor):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.SUPPLIER_CHANGED,
        record_type="SUPPLIER",
        record_ref=ref,
        before=before,
        after=after,
        summary="Supplier oversight decision retained with source and review date.",
    )


def save(db, ref, payload, actor):
    if not ref.strip() or len(ref) > 32:
        raise ProofError("supplier_ref", "Use a nonblank reference of at most 32 characters.")
    row = db.scalar(select(Supplier).where(Supplier.supplier_ref == ref).with_for_update())
    if row and row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the current supplier revision.")
    for field in (
        "name",
        "service",
        "owner",
        "information_access",
        "agreement_terms",
        "shared_responsibility",
        "exit_plan",
    ):
        if not getattr(payload, field).strip():
            raise ProofError(field, "Record the value or an explicit author task.")
    control = lookup(db, Control, Control.control_id, payload.control_ref, "control_ref")
    dependency = lookup(
        db, Supplier, Supplier.supplier_ref, payload.dependency_ref, "dependency_ref"
    )
    seen = {ref}
    cursor = dependency
    while cursor:
        if cursor.supplier_ref in seen:
            raise ProofError("dependency_ref", "Supplier dependencies cannot form a cycle.")
        seen.add(cursor.supplier_ref)
        cursor = db.get(Supplier, cursor.dependency_id) if cursor.dependency_id else None
    if payload.agreement_attachment_id:
        attachment = db.get(EvidenceAttachment, payload.agreement_attachment_id)
        if attachment is None or attachment.purged_on:
            raise ProofError(
                "agreement_attachment_id", "Choose an existing retained agreement attachment."
            )
    before = snapshot(row) if row else None
    if row is None:
        row = Supplier(supplier_ref=ref, revision=0)
        db.add(row)
    for field, value in payload.model_dump(
        exclude={"control_ref", "dependency_ref", "expected_revision"}
    ).items():
        setattr(row, field, value)
    row.control_id = control.id
    row.dependency_id = dependency.id if dependency else None
    row.status, row.reviewed_on = "DRAFT", None
    row.revision += 1
    record(db, ref, before, snapshot(row), actor)
    return row


def review(db, row, payload, actor):
    if row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the current supplier revision.")
    if not payload.reviewed_on <= clock.today() or payload.next_review <= max(
        payload.reviewed_on, clock.today()
    ):
        raise ProofError("next_review", "Use an actual review date and a future next review.")
    last = db.scalar(
        select(SupplierReview)
        .where(SupplierReview.supplier_id == row.id)
        .order_by(SupplierReview.id.desc())
    )
    if last and payload.reviewed_on < last.reviewed_on:
        raise ProofError("reviewed_on", "A review cannot predate the latest retained decision.")
    required(
        [
            payload.note,
            row.owner,
            row.information_access,
            row.agreement_terms,
            row.shared_responsibility,
            row.exit_plan,
        ]
    )
    if row.criticality == "UNASSESSED":
        raise ProofError("criticality", "Assess criticality before signing the review.")
    if payload.result in ("ACTION_REQUIRED", "EXIT"):
        required([payload.action or "", payload.action_owner or ""], "action")
        if payload.action_due is None or payload.action_due < payload.reviewed_on:
            raise ProofError(
                "action_due", "Record an owned action with a deadline on or after review."
            )
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    before = snapshot(row)
    row.review_date, row.reviewed_on = payload.next_review, payload.reviewed_on
    row.status = "EXITED" if payload.result == "EXIT" else "REVIEWED"
    row.revision += 1
    item = SupplierReview(
        supplier_id=row.id,
        actor=actor.username,
        evidence_id=evidence.id,
        snapshot=snapshot(row),
        **payload.model_dump(exclude={"expected_revision", "next_review", "evidence_ref"}),
    )
    db.add(item)
    record(
        db, row.supplier_ref, before, {"supplier": snapshot(row), "review": snapshot(item)}, actor
    )
    return item


def complete(db, item, payload, actor):
    if not item.action or item.completed_on:
        raise ProofError("action", "Only an open agreed action can be completed.")
    if not item.reviewed_on <= payload.completed_on <= clock.today():
        raise ProofError("completed_on", "Use an actual completion date on or after review.")
    required([payload.note])
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    before = snapshot(item)
    item.completed_on, item.completion_note, item.completion_evidence_id = (
        payload.completed_on,
        payload.note,
        evidence.id,
    )
    record(db, db.get(Supplier, item.supplier_id).supplier_ref, before, snapshot(item), actor)
