"""Explicit assurance decisions with retained inputs, actions and effectiveness proof."""

from sqlalchemy import select

from app.core import clock
from app.models.assurance import (
    AssuranceAction,
    AssuranceCycle,
    AssuranceInput,
    AuditProgramme,
    CorrectiveVerification,
)
from app.models.audit import AuditFinding, InternalAudit, ManagementReview, Nonconformity
from app.models.audit_trail import AuditAction
from app.models.soa import Evidence
from app.services import audit_trail
from app.services.context import authored
from app.services.control_testing import AuditStatus, NonconformityStatus
from app.services.planning import authority, lookup
from app.services.provenance import ProofError

REVIEW_INPUTS = (
    "PREVIOUS_ACTIONS",
    "CONTEXT_CHANGES",
    "PARTY_REQUIREMENTS",
    "NONCONFORMITIES_CORRECTIVE_ACTIONS",
    "MONITORING_RESULTS",
    "AUDIT_RESULTS",
    "OBJECTIVES",
    "PARTY_FEEDBACK",
    "RISK_ASSESSMENT_TREATMENT",
    "IMPROVEMENT_OPPORTUNITIES",
)
AUDIT_FIELDS = (
    "title",
    "scope",
    "objectives",
    "criteria",
    "auditor",
    "independence_note",
    "planned_start",
    "planned_end",
    "actual_start",
    "actual_end",
    "outcome_summary",
)
REVIEW_FIELDS = (
    "review_date",
    "chair",
    "attendees",
    "inputs_considered",
    "decisions",
    "actions",
    "next_review_date",
)
NC_FIELDS = (
    "description",
    "source",
    "identified_date",
    "identified_by",
    "owner",
    "immediate_correction",
    "root_cause_analysis",
    "corrective_action",
    "target_date",
    "finding_id",
    "status",
    "effectiveness_check_date",
    "effectiveness_check_result",
    "closure_date",
)


def snapshot(row):
    return audit_trail.snapshot(
        row,
        tuple(c.name for c in row.__table__.columns if c.name not in ("created_at", "updated_at")),
    )


def record(db, actor, ref, before, after):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.ASSURANCE_CHANGED,
        record_type="ASSURANCE",
        record_ref=ref,
        before=before,
        after=after,
        summary="Assurance record changed with explicit supporting inputs and retained actor history.",
    )


def required(values, field="note"):
    if not authored(values):
        raise ProofError(
            field,
            "Complete the authored fields; unresolved author hints cannot support this decision.",
        )


def ref_valid(ref):
    if not ref.strip() or len(ref) > 24:
        raise ProofError("reference", "Use a nonblank reference of at most 24 characters.")


def programme(db, ref, payload, actor):
    ref_valid(ref)
    if payload.ends_on < payload.starts_on or payload.review_date < payload.starts_on:
        raise ProofError("review_date", "Programme end and review cannot precede its start.")
    row = db.scalar(
        select(AuditProgramme).where(AuditProgramme.programme_ref == ref).with_for_update()
    )
    before = snapshot(row) if row else None
    if row and row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the current programme before editing.")
    if row is None:
        row = AuditProgramme(programme_ref=ref, revision=0)
        db.add(row)
    for field, value in payload.model_dump(exclude={"expected_revision"}).items():
        setattr(row, field, value)
    row.revision += 1
    record(db, actor, ref, before, snapshot(row))
    return row


def cycle(db, ref, payload, actor, kind):
    ref_valid(ref)
    row = db.scalar(select(AssuranceCycle).where(AssuranceCycle.cycle_ref == ref).with_for_update())
    if row and (
        row.kind != kind or row.status == "COMPLETED" or row.revision != payload.expected_revision
    ):
        raise ProofError(
            "expected_revision",
            "Edit the current unfinished cycle only; completed records remain frozen.",
        )
    model = InternalAudit if kind == "AUDIT" else ManagementReview
    column = InternalAudit.audit_ref if kind == "AUDIT" else ManagementReview.review_ref
    original = (
        lookup(db, model, column, ref, "reference")
        if row
        else db.scalar(select(model).where(column == ref))
    )
    if original is not None and row is None:
        raise ProofError(
            "reference",
            "Historical records are retained as supplied. Use a new reference for a maintained cycle.",
        )
    before = {"cycle": snapshot(row), "record": snapshot(original)} if row else None
    if kind == "AUDIT":
        plan = lookup(
            db, AuditProgramme, AuditProgramme.programme_ref, payload.programme_ref, "programme_ref"
        )
        if not plan.starts_on <= payload.planned_start <= payload.planned_end <= plan.ends_on:
            raise ProofError("planned_end", "Audit dates must fall within the linked programme.")
        if (
            (payload.actual_end and not payload.actual_start)
            or (payload.actual_start and payload.actual_start > clock.today())
            or (
                payload.actual_end
                and not payload.actual_start <= payload.actual_end <= clock.today()
            )
        ):
            raise ProofError(
                "actual_end", "Actual dates must be ordered and cannot be in the future."
            )
    else:
        plan = None
        if payload.next_review_date <= payload.review_date:
            raise ProofError("next_review_date", "The next review must follow this review.")
    if row is None:
        original = model(
            **(
                {"audit_ref": ref, "status": AuditStatus.PLANNED}
                if kind == "AUDIT"
                else {"review_ref": ref}
            )
        )
        db.add(original)
    for field in AUDIT_FIELDS if kind == "AUDIT" else REVIEW_FIELDS:
        setattr(original, field, getattr(payload, field))
    db.flush()
    if row is None:
        row = AssuranceCycle(
            cycle_ref=ref,
            kind=kind,
            audit_id=original.id if kind == "AUDIT" else None,
            review_id=original.id if kind == "REVIEW" else None,
            programme_id=plan.id if plan else None,
            status="DRAFT",
            revision=0,
        )
        db.add(row)
    row.programme_id = plan.id if plan else None
    row.revision += 1
    if kind == "AUDIT":
        original.status = AuditStatus.IN_PROGRESS if payload.actual_start else AuditStatus.PLANNED
        row.status = "IN_PROGRESS" if payload.actual_start else "DRAFT"
    record(db, actor, ref, before, {"cycle": snapshot(row), "record": snapshot(original)})
    return row


def input_record(db, row, category, payload, actor):
    if row.kind != "REVIEW" or row.status == "COMPLETED" or category not in REVIEW_INPUTS:
        raise ProofError(
            "category", "Use a required input category on an unfinished management review."
        )
    required([payload.consideration], "consideration")
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    if evidence is None:
        required([payload.no_evidence_reason or ""], "no_evidence_reason")
    item = db.scalar(
        select(AssuranceInput).where(
            AssuranceInput.cycle_id == row.id, AssuranceInput.category == category
        )
    )
    before = snapshot(item) if item else None
    if item is None:
        item = AssuranceInput(cycle_id=row.id, category=category)
        db.add(item)
    item.consideration, item.evidence_id, item.no_evidence_reason = (
        payload.consideration,
        evidence.id if evidence else None,
        payload.no_evidence_reason,
    )
    row.revision += 1
    record(db, actor, row.cycle_ref, before, snapshot(item))
    return item


def action(db, row, payload, actor):
    if row.status == "COMPLETED":
        raise ProofError("status", "Record agreed actions before completing the cycle.")
    required([payload.description, payload.owner], "owner")
    if payload.due_date < clock.today():
        raise ProofError("due_date", "A new action needs a current or future due date.")
    finding = lookup(db, AuditFinding, AuditFinding.finding_ref, payload.finding_ref, "finding_ref")
    item = AssuranceAction(
        action_ref=payload.action_ref,
        cycle_id=row.id,
        description=payload.description,
        owner=payload.owner,
        due_date=payload.due_date,
        finding_id=finding.id if finding else None,
        status="OPEN",
    )
    db.add(item)
    row.revision += 1
    record(db, actor, payload.action_ref, None, snapshot(item))
    return item


def completion_evidence(db, payload):
    required([payload.note])
    if payload.completed_on > clock.today():
        raise ProofError("completed_on", "Completion cannot be in the future.")
    return lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")


def complete(db, row, payload, actor):
    evidence = completion_evidence(db, payload)
    if row.status == "COMPLETED":
        raise ProofError("status", "This assurance cycle is already complete.")
    if row.kind == "REVIEW":
        authority(db, actor)
        original = db.get(ManagementReview, row.review_id)
        inputs = list(db.scalars(select(AssuranceInput).where(AssuranceInput.cycle_id == row.id)))
        missing = set(REVIEW_INPUTS) - {x.category for x in inputs}
        if missing:
            raise ProofError(
                "inputs", "Consider every required input: " + ", ".join(sorted(missing))
            )
        required(
            [
                getattr(original, f)
                for f in ("chair", "attendees", "inputs_considered", "decisions", "actions")
            ]
        )
        if not original.review_date <= payload.completed_on:
            raise ProofError("completed_on", "Complete the review on or after its meeting date.")
    else:
        original = db.get(InternalAudit, row.audit_id)
        plan = db.get(AuditProgramme, row.programme_id)
        required(
            [
                original.title,
                original.scope,
                original.objectives,
                original.criteria,
                original.auditor,
                original.independence_note,
                original.outcome_summary or "",
                plan.owner,
                plan.risk_basis,
                plan.coverage,
                plan.frequency,
                plan.methods,
                plan.reporting,
            ]
        )
        if (
            original.actual_start is None
            or original.actual_end is None
            or payload.completed_on < original.actual_end
        ):
            raise ProofError("actual_end", "Record the actual audit period before completion.")
        inputs = []
        original.status = AuditStatus.COMPLETED
    actions = list(db.scalars(select(AssuranceAction).where(AssuranceAction.cycle_id == row.id)))
    row.completion_snapshot = {
        "record": snapshot(original),
        "inputs": [snapshot(x) for x in inputs],
        "actions": [snapshot(x) for x in actions],
        "note": payload.note,
        "evidence_ref": payload.evidence_ref,
    }
    if row.kind == "AUDIT":
        row.completion_snapshot["programme"] = snapshot(plan)
    row.status, row.completed_on, row.completed_by, row.evidence_id = (
        "COMPLETED",
        payload.completed_on,
        actor.username,
        evidence.id,
    )
    record(db, actor, row.cycle_ref, {"status": "UNFINISHED"}, snapshot(row))


def complete_action(db, row, payload, actor):
    evidence = completion_evidence(db, payload)
    if row.status == "COMPLETED":
        raise ProofError("status", "The action is already complete.")
    before = snapshot(row)
    row.status, row.evidence_id, row.completed_on, row.completed_by, row.completion_note = (
        "COMPLETED",
        evidence.id,
        payload.completed_on,
        actor.username,
        payload.note,
    )
    record(db, actor, row.action_ref, before, snapshot(row))


def nonconformity(db, ref, payload, actor):
    ref_valid(ref)
    required(
        [payload.description, payload.identified_by, payload.owner, payload.immediate_correction],
        "immediate_correction",
    )
    if payload.identified_date > clock.today() or (
        payload.target_date and payload.target_date < payload.identified_date
    ):
        raise ProofError(
            "target_date",
            "Use an actual identification date and a subsequent corrective-action target.",
        )
    finding = lookup(db, AuditFinding, AuditFinding.finding_ref, payload.finding_ref, "finding_ref")
    row = db.scalar(select(Nonconformity).where(Nonconformity.nc_ref == ref).with_for_update())
    if row and row.status == NonconformityStatus.CLOSED:
        raise ProofError(
            "status",
            "Closed corrective actions are frozen; an ineffective verification can reopen them.",
        )
    before = snapshot(row) if row else None
    if row is None:
        row = Nonconformity(nc_ref=ref, status=NonconformityStatus.CORRECTION_APPLIED)
        db.add(row)
    for field, value in payload.model_dump(exclude={"finding_ref"}).items():
        setattr(row, field, value)
    row.finding_id = finding.id if finding else None
    if authored([row.root_cause_analysis or "", row.corrective_action or ""]) and row.target_date:
        row.status = NonconformityStatus.AWAITING_EFFECTIVENESS_CHECK
    else:
        row.status = NonconformityStatus.CORRECTION_APPLIED
    record(db, actor, ref, before, snapshot(row))
    return row


def verify(db, row, payload, actor):
    required([payload.note, row.root_cause_analysis or "", row.corrective_action or ""])
    if row.target_date is None or not row.identified_date <= payload.checked_on <= clock.today():
        raise ProofError(
            "checked_on",
            "Verification needs a corrective-action target and an actual check date after identification.",
        )
    last = db.scalar(
        select(CorrectiveVerification)
        .where(CorrectiveVerification.nonconformity_id == row.id)
        .order_by(CorrectiveVerification.id.desc())
    )
    if last and payload.checked_on < last.checked_on:
        raise ProofError(
            "checked_on", "A subsequent verification cannot precede the retained latest check."
        )
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    before = snapshot(row)
    verification = CorrectiveVerification(
        nonconformity_id=row.id,
        checked_on=payload.checked_on,
        result=payload.result,
        note=payload.note,
        evidence_id=evidence.id,
        actor=actor.username,
        snapshot=before,
    )
    db.add(verification)
    row.effectiveness_check_date, row.effectiveness_check_result = (
        payload.checked_on,
        payload.result + ": " + payload.note,
    )
    row.status = (
        NonconformityStatus.CLOSED
        if payload.result == "EFFECTIVE"
        else NonconformityStatus.CORRECTIVE_ACTION_IN_PROGRESS
    )
    row.closure_date = payload.checked_on if payload.result == "EFFECTIVE" else None
    record(
        db,
        actor,
        row.nc_ref,
        before,
        {"record": snapshot(row), "verification": snapshot(verification)},
    )
    return verification
