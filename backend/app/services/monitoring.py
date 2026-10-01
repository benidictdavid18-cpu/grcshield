from sqlalchemy import select

from app.core import clock
from app.models.audit_trail import AuditAction
from app.models.kri import KriDefinition
from app.models.monitoring import MeasurementPlan, MonitoringObservation, RiskAssessmentSnapshot
from app.models.soa import Evidence, RemediationItem
from app.services import audit_trail
from app.services.assurance import required, snapshot
from app.services.planning import lookup
from app.services.provenance import ProofError


def record(db, ref, before, after, actor):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.MONITORING_CHANGED,
        record_type="MONITORING",
        record_ref=ref,
        before=before,
        after=after,
        summary="Measurement basis and evaluation retained without backfilling history.",
    )


def plan(db, ref, payload, actor):
    kri = lookup(db, KriDefinition, KriDefinition.kri_ref, ref, "kri_ref")
    row = db.scalar(
        select(MeasurementPlan).where(MeasurementPlan.kri_id == kri.id).with_for_update()
    )
    if row and row.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Reload the current measurement definition.")
    for field in (
        "method",
        "population",
        "source",
        "collection_owner",
        "evaluation_owner",
        "frequency",
    ):
        if not getattr(payload, field).strip():
            raise ProofError(field, "Supply this field or an explicit author task.")
    before = snapshot(row) if row else None
    if row is None:
        row = MeasurementPlan(kri_id=kri.id, revision=0)
        db.add(row)
    for field, value in payload.model_dump(exclude={"expected_revision"}).items():
        setattr(row, field, value)
    row.revision += 1
    record(db, ref, before, snapshot(row), actor)
    return row


def observe(db, plan, payload, actor):
    if plan.revision != payload.expected_revision:
        raise ProofError("expected_revision", "Collect against the current measurement definition.")
    required(
        [
            plan.method,
            plan.population,
            plan.source,
            plan.collection_owner,
            plan.evaluation_owner,
            plan.frequency,
            payload.source_query,
            payload.population,
        ]
    )
    if not payload.period_start <= payload.period_end <= clock.today():
        raise ProofError("period_end", "Record an actual ordered measurement period.")
    kri = db.get(KriDefinition, plan.kri_id)
    if payload.value is not None and (
        payload.value < 0 or (kri.unit.value == "PERCENT" and payload.value > 100)
    ):
        raise ProofError("value", "Use a nonnegative observation; percentages cannot exceed 100.")
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    row = MonitoringObservation(
        plan_id=plan.id,
        actor=actor.username,
        evidence_id=evidence.id,
        band=kri.band_for(payload.value).value,
        definition_snapshot={"plan": snapshot(plan), "kri": snapshot(kri)},
        **payload.model_dump(exclude={"expected_revision", "evidence_ref"}),
    )
    db.add(row)
    record(db, kri.kri_ref, None, snapshot(row), actor)
    return row


def evaluate(db, row, payload, actor):
    if row.evaluated_on:
        raise ProofError("evaluated_on", "This observation already has a retained evaluation.")
    if not row.period_end <= payload.evaluated_on <= clock.today():
        raise ProofError(
            "evaluated_on", "Evaluate on or after the observed period, not in the future."
        )
    required([payload.note])
    remediation = lookup(
        db,
        RemediationItem,
        RemediationItem.remediation_ref,
        payload.remediation_ref,
        "remediation_ref",
    )
    if row.band == "RED" and (remediation is None or not remediation.is_open):
        raise ProofError(
            "remediation_ref", "A red observation needs an open owned remediation for follow-up."
        )
    before = snapshot(row)
    row.evaluated_on, row.evaluated_by, row.evaluation = (
        payload.evaluated_on,
        actor.username,
        payload.note,
    )
    row.remediation_id = remediation.id if remediation else None
    record(db, str(row.id), before, snapshot(row), actor)


def capture_risk(db, risk, actor, basis):
    data = snapshot(risk)
    data["control_links"] = [snapshot(x) for x in risk.control_links]
    row = RiskAssessmentSnapshot(
        risk_id=risk.id, assessed_on=clock.today(), actor=actor.username, basis=basis, snapshot=data
    )
    db.add(row)
    return row
