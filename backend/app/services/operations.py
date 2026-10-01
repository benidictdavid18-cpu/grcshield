"""Reviewed revisions update existing registers through their established rules."""

import json
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import delete, select

from app.core import clock
from app.models import privacy as m
from app.models.audit_trail import AuditAction
from app.models.operations import (
    ContinuityExercise,
    OperationalEvidence,
    OperationalReviewTask,
    RegisterRevision,
    RiskAsset,
)
from app.models.risk import Control, Risk
from app.models.soa import Evidence
from app.schemas import operations as schemas
from app.services import audit_trail
from app.services.assurance import required
from app.services.assurance import snapshot as raw_snapshot
from app.services.people import reference
from app.services.planning import lookup
from app.services.privacy_continuity import validate_bia, validate_dpia, validate_ropa
from app.services.provenance import ProofError

KINDS = {
    "ASSET": (m.Asset, "asset_ref", schemas.AssetIn),
    "ROPA": (m.RopaEntry, "ropa_ref", schemas.RopaIn),
    "DPIA": (m.Dpia, "dpia_ref", schemas.DpiaIn),
    "BIA": (m.BusinessImpactAnalysis, "bia_ref", schemas.BiaIn),
}
LINKS = {
    "ROPA": [
        (m.RopaAssetLink, "asset", m.Asset, "asset_ref"),
        (m.RopaRiskLink, "risk", Risk, "risk_ref"),
        (m.RopaControlLink, "control", Control, "control_id"),
    ],
    "DPIA": [
        (m.DpiaAssetLink, "asset", m.Asset, "asset_ref"),
        (m.DpiaRiskLink, "risk", Risk, "risk_ref"),
    ],
    "BIA": [
        (m.BiaAssetLink, "asset", m.Asset, "asset_ref"),
        (m.BiaRiskLink, "risk", Risk, "risk_ref"),
        (m.BiaControlLink, "control", Control, "control_id"),
    ],
}


def snapshot(row):
    return json.loads(
        json.dumps(
            raw_snapshot(row), default=lambda x: float(x) if isinstance(x, Decimal) else str(x)
        )
    )


def record(db, ref, before, after, actor):
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.OPERATIONAL_CHANGED,
        record_type="OPERATIONAL_REGISTER",
        record_ref=ref,
        before=before,
        after=after,
        summary="Operational revision retained; linked risk owners must reassess material changes.",
    )


def current(db, kind, ref):
    model, key, _ = KINDS[kind]
    return db.scalar(select(model).where(getattr(model, key) == ref).with_for_update())


def view(db, kind, row):
    if row is None:
        return None
    data = snapshot(row)
    if kind == "ASSET":
        data["risk_refs"] = [
            x.risk_ref
            for x in db.scalars(
                select(Risk)
                .join(RiskAsset)
                .where(RiskAsset.asset_id == row.id)
                .order_by(Risk.risk_ref)
            )
        ]
    else:
        for _, name, _, key in LINKS[kind]:
            data[name + "_refs"] = [getattr(x, key) for x in getattr(row, "linked_" + name + "s")]
    return data


def validate(db, kind, content):
    try:
        payload = KINDS[kind][2].model_validate(content)
    except ValidationError as exc:
        error = exc.errors()[0]
        raise ProofError("content." + ".".join(str(x) for x in error["loc"]), error["msg"]) from exc
    values = payload.model_dump()
    rules = {
        "ROPA": (
            validate_ropa,
            (
                "transfers_outside_eea",
                "transfer_safeguard",
                "transfer_detail",
                "retention_period",
                "lawful_basis",
                "legitimate_interests_assessment",
            ),
        ),
        "DPIA": (
            validate_dpia,
            (
                "outcome",
                "residual_risk",
                "dpo_consulted",
                "supervisory_authority_consulted",
                "mitigating_measures",
                "review_date",
            ),
        ),
        "BIA": (validate_bia, ("rto_hours", "rpo_hours", "mtpd_hours")),
    }
    if kind in rules:
        fn, fields = rules[kind]
        errors = fn(**{f: values[f] for f in fields})
        if errors:
            raise ProofError("content." + errors[0].field, errors[0].message)
    for key, value in values.items():
        if isinstance(value, str) and not value.strip():
            raise ProofError("content." + key, "Text fields cannot be blank.")
    if kind == "DPIA" and (
        payload.assessment_date > clock.today() or payload.review_date <= payload.assessment_date
    ):
        raise ProofError(
            "content.review_date", "Use an actual assessment date and a later review date."
        )
    supported = {
        "ASSET": {"risk"},
        "ROPA": {"asset", "risk", "control"},
        "DPIA": {"asset", "risk"},
        "BIA": {"asset", "risk", "control"},
    }[kind]
    for name, model, key in [
        ("asset", m.Asset, "asset_ref"),
        ("risk", Risk, "risk_ref"),
        ("control", Control, "control_id"),
    ]:
        refs = getattr(payload, name + "_refs")
        if refs and name not in supported:
            raise ProofError(
                "content." + name + "_refs", "This record kind does not support these links."
            )
        if len(set(refs)) != len(refs):
            raise ProofError("content." + name + "_refs", "Duplicate links are not permitted.")
        for ref in refs:
            lookup(db, model, getattr(model, key), ref, name + "_refs")
    if kind == "DPIA" and payload.ropa_ref:
        lookup(db, m.RopaEntry, m.RopaEntry.ropa_ref, payload.ropa_ref, "ropa_ref")
    return payload


def propose(db, payload, actor):
    reference(payload.record_ref)
    old = current(db, payload.kind, payload.record_ref)
    last = db.scalar(
        select(RegisterRevision)
        .where(
            RegisterRevision.kind == payload.kind, RegisterRevision.record_ref == payload.record_ref
        )
        .order_by(RegisterRevision.revision.desc())
    )
    revision = last.revision if last else 0
    if payload.expected_revision != revision:
        raise ProofError("expected_revision", "Reload the current proposal history.")
    required([payload.change_note], "change_note")
    parsed = validate(db, payload.kind, payload.content)
    item = RegisterRevision(
        kind=payload.kind,
        record_ref=payload.record_ref,
        revision=revision + 1,
        owner=payload.owner,
        review_date=payload.review_date,
        change_note=payload.change_note,
        actor=actor.username,
        content=parsed.model_dump(mode="json"),
        previous=view(db, payload.kind, old),
    )
    db.add(item)
    record(
        db,
        payload.record_ref,
        None,
        {"revision": revision + 1, "content": item.content, "previous": item.previous},
        actor,
    )
    return item


def review(db, item, payload, actor):
    if item.status != "DRAFT":
        raise ProofError("status", "This revision is already reviewed.")
    required([item.owner, payload.note, json.dumps(item.content)], "content")
    if not payload.completed_on <= clock.today() < item.review_date:
        raise ProofError("completed_on", "Use an actual review date and future next review date.")
    row = current(db, item.kind, item.record_ref)
    if view(db, item.kind, row) != item.previous:
        raise ProofError(
            "revision",
            "The source register changed; prepare a new revision against its current state.",
        )
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    parsed = validate(db, item.kind, item.content)
    model, key, _ = KINDS[item.kind]
    if row is None:
        row = model(**{key: item.record_ref})
        db.add(row)
    for field, value in parsed.model_dump(
        exclude={"asset_refs", "risk_refs", "control_refs", "ropa_ref"}
    ).items():
        setattr(row, field, value)
    if item.kind == "DPIA":
        ropa = lookup(db, m.RopaEntry, m.RopaEntry.ropa_ref, parsed.ropa_ref, "ropa_ref")
        row.ropa_id = ropa.id if ropa else None
    if item.kind in ("ROPA", "BIA"):
        row.last_reviewed = payload.completed_on
    db.flush()
    if item.kind == "ASSET":
        db.execute(delete(RiskAsset).where(RiskAsset.asset_id == row.id))
        for ref in parsed.risk_refs:
            db.add(
                RiskAsset(
                    asset_id=row.id, risk_id=lookup(db, Risk, Risk.risk_ref, ref, "risk_refs").id
                )
            )
    else:
        for link, name, target, refkey in LINKS[item.kind]:
            relation = name + "_links"
            collection = getattr(row, relation)
            collection.clear()
            db.flush()
            for ref in getattr(parsed, name + "_refs"):
                target_row = lookup(db, target, getattr(target, refkey), ref, name + "_refs")
                collection.append(link(**{name + "_id": target_row.id}))
    item.status, item.reviewed_by, item.reviewed_on, item.evidence_id = (
        "REVIEWED",
        actor.username,
        payload.completed_on,
        evidence.id,
    )
    refs = set(parsed.risk_refs) | set((item.previous or {}).get("risk_refs", []))
    if item.kind == "ASSET":
        for link, owner_type, owner_key in [
            (m.RopaAssetLink, m.RopaEntry, "ropa_id"),
            (m.DpiaAssetLink, m.Dpia, "dpia_id"),
            (m.BiaAssetLink, m.BusinessImpactAnalysis, "bia_id"),
        ]:
            for dependent in db.scalars(
                select(owner_type)
                .join(link, getattr(link, owner_key) == owner_type.id)
                .where(link.asset_id == row.id)
            ):
                refs.update(x.risk_ref for x in dependent.linked_risks)
    for ref in sorted(refs):
        risk = lookup(db, Risk, Risk.risk_ref, ref, "risk_refs")
        db.add(OperationalReviewTask(revision_id=item.id, risk_id=risk.id, owner=risk.owner_role))
    record(
        db,
        item.record_ref,
        item.previous,
        {"reviewed": view(db, item.kind, row), "revision": item.revision, "note": payload.note},
        actor,
    )


def resolve(db, row, payload, actor):
    if row.status == "RESOLVED":
        raise ProofError("status", "This reassessment is already resolved.")
    required([payload.note])
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    before = snapshot(row)
    row.status, row.resolution, row.evidence_id, row.resolved_by = (
        "RESOLVED",
        payload.note,
        evidence.id,
        actor.username,
    )
    record(db, str(row.id), before, snapshot(row), actor)


def coverage(db, payload, actor):
    required([payload.source_system, payload.owner, payload.coverage_note])
    if (
        not payload.period_start <= payload.period_end <= clock.today()
        or payload.review_date < payload.period_end
    ):
        raise ProofError(
            "period_end", "Use an actual ordered evidence period and subsequent review date."
        )
    control = lookup(db, Control, Control.control_id, payload.control_ref, "control_ref")
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    item = OperationalEvidence(
        control_id=control.id,
        evidence_id=evidence.id,
        actor=actor.username,
        **payload.model_dump(exclude={"control_ref", "evidence_ref"}),
    )
    db.add(item)
    record(db, control.control_id, None, snapshot(item), actor)
    return item


def exercise(db, ref, payload, actor):
    reference(ref)
    required([payload.note, payload.follow_up])
    if payload.performed_on > clock.today():
        raise ProofError("performed_on", "Record an actual exercise date.")
    bia = lookup(
        db, m.BusinessImpactAnalysis, m.BusinessImpactAnalysis.bia_ref, payload.bia_ref, "bia_ref"
    )
    evidence = lookup(db, Evidence, Evidence.evidence_ref, payload.evidence_ref, "evidence_ref")
    item = ContinuityExercise(
        exercise_ref=ref,
        bia_id=bia.id,
        evidence_id=evidence.id,
        actor=actor.username,
        target_snapshot={
            "rto_hours": bia.rto_hours,
            "rpo_hours": bia.rpo_hours,
            "mtpd_hours": bia.mtpd_hours,
            "targets_met": payload.recovery_hours <= bia.rto_hours
            and payload.data_loss_hours <= bia.rpo_hours,
        },
        **payload.model_dump(exclude={"bia_ref", "evidence_ref"}),
    )
    db.add(item)
    record(db, ref, None, snapshot(item), actor)
    return item
