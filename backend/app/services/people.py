from sqlalchemy import select

from app.core import clock
from app.models.audit_trail import AuditAction
from app.models.document import DocumentRevision
from app.models.people import CommunicationPlan, CompetenceEvaluation, CompetenceRequirement
from app.models.soa import Evidence
from app.services import audit_trail
from app.services.assurance import required, snapshot
from app.services.planning import lookup
from app.services.provenance import ProofError


def record(db, ref, before, after, actor):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.COMPETENCE_CHANGED,
        record_type="PEOPLE",
        record_ref=ref,
        before=before,
        after=after,
        summary="Competence or communication record maintained; attendance is not competence.",
    )


def reference(ref):
    if not ref.strip() or len(ref) > 32:
        raise ProofError("reference", "Use a nonblank reference of at most 32 characters.")


def requirement(db, ref, payload, actor):
    reference(ref)
    row = db.scalar(
        select(CompetenceRequirement)
        .where(CompetenceRequirement.requirement_ref == ref)
        .with_for_update()
    )
    if row and row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the current role requirement.")
    for field in ("role", "requirement", "evaluation_method", "owner"):
        if not getattr(payload, field).strip():
            raise ProofError(field, "Record the requirement or an explicit author task.")
    before = snapshot(row) if row else None
    if row is None:
        row = CompetenceRequirement(requirement_ref=ref, revision=0)
        db.add(row)
    for field, value in payload.model_dump(exclude={"expected_revision"}).items():
        setattr(row, field, value)
    row.revision += 1
    record(db, ref, before, snapshot(row), actor)
    return row


def evaluate(db, row, payload, actor):
    if row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Evaluate the current requirement revision.")
    required(
        [
            row.requirement,
            row.evaluation_method,
            row.owner,
            payload.subject_ref,
            payload.demonstrated_outcome,
        ]
    )
    if not payload.evaluated_on <= clock.today() < payload.review_date:
        raise ProofError("review_date", "Record an actual evaluation and future review date.")
    if payload.result == "DEVELOPMENT_REQUIRED":
        required([payload.development_action or ""], "development_action")
        if payload.action_due is None or payload.action_due < payload.evaluated_on:
            raise ProofError(
                "action_due",
                "Development work needs a dated commitment owned by the requirement owner.",
            )
    last = db.scalar(
        select(CompetenceEvaluation)
        .where(
            CompetenceEvaluation.requirement_id == row.id,
            CompetenceEvaluation.subject_ref == payload.subject_ref,
        )
        .order_by(CompetenceEvaluation.id.desc())
    )
    if last and payload.evaluated_on < last.evaluated_on:
        raise ProofError("evaluated_on", "Do not backdate a subsequent evaluation.")
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    item = CompetenceEvaluation(
        requirement_id=row.id,
        actor=actor.username,
        evidence_id=evidence.id,
        requirement_snapshot=snapshot(row),
        **payload.model_dump(exclude={"expected_revision", "evidence_ref"}),
    )
    db.add(item)
    # Personnel evidence is deliberately not copied into the broadly readable audit trail.
    record(
        db,
        row.requirement_ref,
        None,
        {"subject_recorded": True, "requirement_revision": row.revision},
        actor,
    )
    return item


def communication(db, ref, payload, actor):
    reference(ref)
    required([payload.topic, payload.audience, payload.owner, payload.method])
    if db.scalar(select(CommunicationPlan.id).where(CommunicationPlan.communication_ref == ref)):
        raise ProofError(
            "reference",
            "This plan already exists; retain it and use a new reference for a new communication.",
        )
    if payload.document_revision_id:
        revision = db.get(DocumentRevision, payload.document_revision_id)
        if revision is None or revision.status != "PUBLISHED":
            raise ProofError(
                "document_revision_id",
                "Awareness communication must cite a published policy revision.",
            )
    row = CommunicationPlan(communication_ref=ref, **payload.model_dump())
    db.add(row)
    db.flush()
    record(db, ref, None, snapshot(row), actor)
    return row


def deliver(db, row, payload, actor):
    if row.status == "DELIVERED" or payload.completed_on > clock.today():
        raise ProofError("completed_on", "Record an actual delivery once.")
    required([payload.note])
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    before = snapshot(row)
    row.status, row.delivered_on, row.delivered_by = (
        "DELIVERED",
        payload.completed_on,
        actor.username,
    )
    row.evidence_id, row.outcome = evidence.id, payload.note
    record(db, row.communication_ref, before, snapshot(row), actor)
