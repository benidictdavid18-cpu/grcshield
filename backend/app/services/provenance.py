"""Test provenance supplements ADR-008; it never computes a residual score."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.audit import ControlTest
from app.models.provenance import Reassessment, TestDisposition
from app.models.risk import RiskControl
from app.models.soa import Evidence, SoAEntry, SoAControlLink
from app.models.privacy import RopaEntry, RopaControlLink, Dpia, DpiaRiskLink, BusinessImpactAnalysis, BiaControlLink
from app.models.audit_trail import AuditAction
from app.services import audit_trail
from app.services.control_testing import CONCLUSION_TO_OPERATING, TestConclusion, OperatingEffectiveness, validate_effectiveness

BASIS_RANK = {"TESTED_INEFFECTIVE": 0, "TESTED_WITH_EXCEPTIONS": 1, "TESTED_EFFECTIVE": 2}
TEST_RANK = {"FAIL": 0, "PASS_WITH_EXCEPTIONS": 1, "PASS": 2}
TODO = "TODO AUTHOR:BENNY - identify the workpaper and population supporting this tested basis."

class ProofError(ValueError):
    def __init__(self, field, message):
        self.field = field
        super().__init__(message)

def bind_proof(db, link, test, note, actor):
    if not note.strip() or "TODO AUTHOR:BENNY" in note:
        raise ProofError("note", "Record the author's population-specific basis before binding proof.")
    if test.control_id != link.control_id:
        raise ProofError("test_ref", "The supporting test must examine the linked control.")
    if db.get(TestDisposition, test.id):
        raise ProofError("test_ref", "Withdrawn or superseded tests cannot support a new claim.")
    if not test.is_reviewed:
        raise ProofError("test_ref", "The supporting workpaper must be reviewed.")
    rank = BASIS_RANK.get(link.effectiveness_basis.value)
    if rank is None or rank > TEST_RANK[test.conclusion.value]:
        raise ProofError("test_ref", "This workpaper does not support the recorded tested basis.")
    before = {"test_id": link.supporting_test_id, "note": link.proof_note}
    link.supporting_test_id, link.proof_note = test.id, note.strip()
    audit_trail.record_change(db, actor=actor, action=AuditAction.PROOF_BOUND,
        record_type="RISK", record_ref=link.risk.risk_ref, before=before,
        after={"test_id": test.id, "test_ref": test.test_ref, "control": link.control.control_id, "note": note.strip()},
        summary="Supporting workpaper and population-specific basis recorded.")

def queue_impacts(db, test, reason):
    links = db.scalars(select(RiskControl).where(RiskControl.control_id == test.control_id)).all()
    targets = {("RISK", l.risk.risk_ref): l.risk.owner_role for l in links}
    for row in db.scalars(select(SoAEntry).join(SoAControlLink).where(SoAControlLink.control_id == test.control_id)):
        targets[("SOA", row.control_ref)] = row.owner
    for row in db.scalars(select(RopaEntry).join(RopaControlLink).where(RopaControlLink.control_id == test.control_id)):
        targets[("ROPA", row.ropa_ref)] = row.owner_role
    ids = [l.risk_id for l in links]
    for row in db.scalars(select(Dpia).join(DpiaRiskLink).where(DpiaRiskLink.risk_id.in_(ids))).unique():
        targets[("DPIA", row.dpia_ref)] = row.assessed_by
    for row in db.scalars(select(BusinessImpactAnalysis).join(BiaControlLink).where(BiaControlLink.control_id == test.control_id)):
        targets[("BIA", row.bia_ref)] = row.owner_role
    for (kind, ref), owner in targets.items():
        existing = db.scalar(select(Reassessment).where(Reassessment.trigger_test_id == test.id, Reassessment.record_type == kind, Reassessment.record_ref == ref))
        if existing is None:
            db.add(Reassessment(trigger_test_id=test.id, record_type=kind, record_ref=ref, owner=owner, reason=reason))

def rollup(db, control):
    # Keep the existing seed's worst-outstanding-result rule at runtime too.
    tests = db.scalars(select(ControlTest).where(ControlTest.control_id == control.id)).all()
    active = [t for t in tests if db.get(TestDisposition, t.id) is None]
    if active:
        worst = min(active, key=lambda t: TEST_RANK[t.conclusion.value])
        implied = CONCLUSION_TO_OPERATING[worst.conclusion]
        if validate_effectiveness(control.design_effectiveness, implied):
            implied = OperatingEffectiveness.EFFECTIVE_WITH_EXCEPTIONS
        control.operating_effectiveness = implied
    else:
        control.operating_effectiveness = OperatingEffectiveness.NOT_TESTED
    control.last_tested = max((t.test_date for t in tests), default=None)

def record_test_impacts(db, test):
    db.flush()
    rollup(db, test.control)
    if test.conclusion != TestConclusion.PASS:
        queue_impacts(db, test, f"{test.test_ref} concluded {test.conclusion.value}; review the linked claim and its population. No score or decision was automatically changed.")

def dispose_test(db, test, replacement, reason, actor):
    if db.get(TestDisposition, test.id):
        raise ProofError("test_ref", "This workpaper already has a disposition.")
    if not reason.strip() or "TODO AUTHOR:BENNY" in reason:
        raise ProofError("reason", "An authored disposition reason is required.")
    if replacement:
        if replacement.id == test.id or replacement.control_id != test.control_id or replacement.population_description.strip() != test.population_description.strip() or replacement.test_date < test.test_date:
            raise ProofError("replacement_ref", "Replacement must be a later test of the same control and declared population.")
        if not replacement.is_reviewed or db.get(TestDisposition, replacement.id):
            raise ProofError("replacement_ref", "Replacement must be reviewed and active.")
    item = TestDisposition(test_id=test.id, replacement_id=replacement.id if replacement else None,
        kind="SUPERSEDED" if replacement else "WITHDRAWN", reason=reason.strip(), actor=actor.username)
    db.add(item)
    db.flush()
    queue_impacts(db, test, f"{test.test_ref} {item.kind.lower()}: {reason.strip()}")
    before = audit_trail.snapshot(test.control, ("operating_effectiveness", "last_tested"))
    rollup(db, test.control)
    audit_trail.record_change(db, actor=actor, action=AuditAction.TEST_DISPOSITION_RECORDED,
        record_type="CONTROL_TEST", record_ref=test.test_ref, before=None,
        after={"kind": item.kind, "replacement_ref": replacement.test_ref if replacement else None, "reason": reason.strip()}, summary="Workpaper disposition recorded; dependent claims require review.")
    after = audit_trail.snapshot(test.control, ("operating_effectiveness", "last_tested"))
    if before != after:
        audit_trail.record_change(db, actor=actor, action=AuditAction.CONTROL_EFFECTIVENESS_UPDATED,
            record_type="CONTROL", record_ref=test.control.control_id, before=before, after=after,
            summary="Active-workpaper rollup changed after an authored test disposition.")
    return item

def resolve(db, item, evidence, resolution, actor):
    if item.status != "OPEN":
        raise ProofError("status", "This reassessment is already resolved.")
    if not resolution.strip() or "TODO AUTHOR:BENNY" in resolution:
        raise ProofError("resolution", "Record an authored resolution and its evidence.")
    item.status, item.resolution = "RESOLVED", resolution.strip()
    item.evidence_id, item.resolved_by = evidence.id, actor.username
    audit_trail.record_change(db, actor=actor, action=AuditAction.REASSESSMENT_RESOLVED,
        record_type=item.record_type, record_ref=item.record_ref, before={"status": "OPEN"},
        after={"status": item.status, "resolution": item.resolution, "evidence_ref": evidence.evidence_ref, "trigger_test_id": item.trigger_test_id}, summary="Reassessment resolved by a human with supporting evidence.")

def proof_summary(db, link):
    test = link.supporting_test
    state = "NOT_REQUIRED" if link.effectiveness_basis.value not in BASIS_RANK else "MISSING"
    if test:
        state = "WITHDRAWN_OR_SUPERSEDED" if db.get(TestDisposition, test.id) else "LINKED"
    pending = db.scalar(select(Reassessment.id).where(Reassessment.record_type == "RISK", Reassessment.record_ref == link.risk.risk_ref, Reassessment.status == "OPEN").join(ControlTest, Reassessment.trigger_test_id == ControlTest.id).where(ControlTest.control_id == link.control_id))
    if pending is not None:
        state = "REASSESSMENT_REQUIRED"
    return dict(supporting_test_ref=test.test_ref if test else None,
        proof_state=state, proof_note=link.proof_note,
        test_population=test.population_description if test else None,
        test_period_start=test.period_covered_start if test else None,
        test_period_end=test.period_covered_end if test else None)
