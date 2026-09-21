"""Milestone progress is delivery evidence, never an automatic residual-risk score."""
from datetime import datetime,timezone
from sqlalchemy import select,delete
from app.core import clock
from app.models.treatment import TreatmentPlan,TreatmentControl,TreatmentMilestone
from app.models.risk import Risk,Control
from app.models.soa import Evidence,RemediationItem
from app.models.audit_trail import AuditAction
from app.services import audit_trail,acceptance
from app.services.context import authored
from app.services.provenance import ProofError

PLAN_FIELDS=("plan_ref","risk_id","title","owner","resources","rationale","review_deadline","status","revision")
MILESTONE_FIELDS=("milestone_ref","title","owner","due_date","dependency_id","remediation_id","status","evidence_id","completion_note","completed_on","completed_by")

def milestones(db,plan): return db.scalars(select(TreatmentMilestone).where(TreatmentMilestone.plan_id==plan.id).order_by(TreatmentMilestone.id)).all()

def save_plan(db,ref,payload,actor):
    if not ref.strip() or len(ref)>32 or not all(getattr(payload,x).strip() for x in ("title","owner","resources","rationale")):
        raise ProofError("plan_ref","Reference, title, owner, resources and rationale are required.")
    risk=db.scalar(select(Risk).where(Risk.risk_ref==payload.risk_ref))
    if risk is None or risk.next_review is None: raise ProofError("risk_ref","Choose a real risk with a next review date.")
    controls=db.scalars(select(Control).where(Control.control_id.in_(payload.control_refs))).all()
    if {c.control_id for c in controls}!=set(payload.control_refs): raise ProofError("control_refs","Every treatment control must exist.")
    row=db.scalar(select(TreatmentPlan).where(TreatmentPlan.plan_ref==ref).with_for_update())
    before=audit_trail.snapshot(row,PLAN_FIELDS) if row else None
    if row and (row.status!="DRAFT" or payload.expected_revision!=row.revision or row.risk_id!=risk.id):
        raise ProofError("expected_revision","Only the current draft can be edited; retain approved plans and create a new plan revision.")
    if row is None:
        row=TreatmentPlan(plan_ref=ref,risk_id=risk.id,status="DRAFT",revision=0)
        db.add(row)
    if row.id and any(m.due_date>risk.next_review for m in milestones(db,row)):
        raise ProofError("review_deadline","Existing milestones exceed the risk review; revise their dates first.")
    for name in ("title","owner","resources","rationale"): setattr(row,name,getattr(payload,name))
    row.review_deadline=risk.next_review
    row.revision+=1
    db.flush()
    db.execute(delete(TreatmentControl).where(TreatmentControl.plan_id==row.id))
    for c in controls: db.add(TreatmentControl(plan_id=row.id,control_id=c.id))
    audit_trail.record_change(db,actor=actor,action=AuditAction.TREATMENT_PLAN_UPDATED,record_type="TREATMENT_PLAN",record_ref=ref,before=before,after={**audit_trail.snapshot(row,PLAN_FIELDS),"controls":payload.control_refs},summary="Draft treatment commitments recorded against the risk review deadline.")
    return row

def save_milestone(db,plan,ref,payload,actor):
    if plan.status!="DRAFT": raise ProofError("status","Milestone commitments are frozen after approval; create a revised plan.")
    if not ref.strip() or len(ref)>32 or not payload.title.strip() or not payload.owner.strip(): raise ProofError("milestone_ref","Milestone reference, title and accountable owner are required.")
    risk=db.get(Risk,plan.risk_id)
    if risk.next_review is None or payload.due_date>min(plan.review_deadline,risk.next_review):
        raise ProofError("due_date","A milestone cannot fall after the risk's next review.")
    row=db.scalar(select(TreatmentMilestone).where(TreatmentMilestone.plan_id==plan.id,TreatmentMilestone.milestone_ref==ref))
    dependency=db.scalar(select(TreatmentMilestone).where(TreatmentMilestone.plan_id==plan.id,TreatmentMilestone.milestone_ref==payload.dependency_ref)) if payload.dependency_ref else None
    if payload.dependency_ref and dependency is None: raise ProofError("dependency_ref","The dependency must exist in this plan.")
    cursor=dependency
    seen=set()
    while cursor:
        if (row and cursor.id==row.id) or cursor.id in seen: raise ProofError("dependency_ref","Milestone dependencies cannot form a cycle.")
        seen.add(cursor.id)
        cursor=db.get(TreatmentMilestone,cursor.dependency_id) if cursor.dependency_id else None
    if dependency and payload.due_date<dependency.due_date: raise ProofError("due_date","A dependent milestone cannot be due before its dependency.")
    if row:
        children=db.scalars(select(TreatmentMilestone).where(TreatmentMilestone.dependency_id==row.id)).all()
        if any(x.due_date<payload.due_date for x in children): raise ProofError("due_date","Move dependent milestones first; this date would exceed their due dates.")
    remediation=db.scalar(select(RemediationItem).where(RemediationItem.remediation_ref==payload.remediation_ref)) if payload.remediation_ref else None
    if payload.remediation_ref and remediation is None: raise ProofError("remediation_ref","Unknown remediation reference.")
    before=audit_trail.snapshot(row,MILESTONE_FIELDS) if row else None
    if row is None:
        row=TreatmentMilestone(plan_id=plan.id,review_deadline=plan.review_deadline,milestone_ref=ref,status="OPEN")
        db.add(row)
    row.title,row.owner,row.due_date=payload.title,payload.owner,payload.due_date
    row.dependency_id=dependency.id if dependency else None
    row.remediation_id=remediation.id if remediation else None
    plan.revision+=1
    audit_trail.record_change(db,actor=actor,action=AuditAction.TREATMENT_MILESTONE_UPDATED,record_type="TREATMENT_PLAN",record_ref=plan.plan_ref,before=before,after=audit_trail.snapshot(row,MILESTONE_FIELDS),summary="A dated milestone and its dependency were recorded without implying effectiveness.")
    return row

def authorize(db,plan,actor):
    risk=db.get(Risk,plan.risk_id)
    if not (acceptance.authority(db,actor,risk.owner_role) or acceptance.authority(db,actor,"Chief Executive Officer")):
        raise PermissionError("Current risk-owner or CEO authority is required for this treatment decision.")
    return risk

def approve(db,plan,note,actor):
    risk=authorize(db,plan,actor)
    rows=milestones(db,plan)
    if plan.status!="DRAFT" or not rows or not authored([note,plan.title,plan.owner,plan.resources,plan.rationale]+[v for m in rows for v in (m.title,m.owner)]):
        raise ProofError("note","An approvable draft needs milestones, resources and resolved author decisions.")
    if risk.next_review is None or plan.review_deadline>risk.next_review or plan.review_deadline<clock.today():
        raise ProofError("review_deadline","The plan must fit a current risk review schedule.")
    plan.approved_snapshot={**audit_trail.snapshot(plan,PLAN_FIELDS),"milestones":[audit_trail.snapshot(m,MILESTONE_FIELDS) for m in rows],"controls":list(db.scalars(select(Control.control_id).join(TreatmentControl).where(TreatmentControl.plan_id==plan.id)))}
    plan.status,plan.approved_by,plan.approved_at,plan.approval_note="APPROVED",actor.username,datetime.now(timezone.utc),note.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.TREATMENT_PLAN_APPROVED,record_type="TREATMENT_PLAN",record_ref=plan.plan_ref,before={"status":"DRAFT"},after={"status":plan.status,"snapshot":plan.approved_snapshot,"note":plan.approval_note},summary="The authorized business owner approved the retained treatment commitments.")

def complete_milestone(db,row,evidence_ref,note,actor):
    plan=db.get(TreatmentPlan,row.plan_id)
    evidence=db.scalar(select(Evidence).where(Evidence.evidence_ref==evidence_ref))
    if plan.status!="APPROVED" or row.status=="COMPLETED" or evidence is None or not authored([note]):
        raise ProofError("evidence_ref","Completion needs an approved plan, an unfinished milestone, real evidence and an authored note.")
    if row.dependency_id and db.get(TreatmentMilestone,row.dependency_id).status!="COMPLETED":
        raise ProofError("dependency_ref","Complete the dependency before this milestone.")
    before=audit_trail.snapshot(row,MILESTONE_FIELDS)
    row.status,row.evidence_id,row.completion_note,row.completed_on,row.completed_by="COMPLETED",evidence.id,note.strip(),clock.today(),actor.username
    audit_trail.record_change(db,actor=actor,action=AuditAction.TREATMENT_MILESTONE_UPDATED,record_type="TREATMENT_PLAN",record_ref=plan.plan_ref,before=before,after=audit_trail.snapshot(row,MILESTONE_FIELDS),summary="Milestone delivery recorded with evidence; residual risk and linked remediation decisions are unchanged.")

def close(db,plan,evidence_ref,note,actor):
    authorize(db,plan,actor)
    evidence=db.scalar(select(Evidence).where(Evidence.evidence_ref==evidence_ref))
    rows=milestones(db,plan)
    if plan.status!="APPROVED" or not rows or any(m.status!="COMPLETED" for m in rows) or evidence is None or not authored([note]):
        raise ProofError("note","Close only after all milestones are complete, with verification evidence and an authored evaluation.")
    plan.status,plan.verification_evidence_id,plan.verification_note,plan.closed_by="COMPLETED",evidence.id,note.strip(),actor.username
    audit_trail.record_change(db,actor=actor,action=AuditAction.TREATMENT_PLAN_CLOSED,record_type="TREATMENT_PLAN",record_ref=plan.plan_ref,before={"status":"APPROVED"},after={"status":plan.status,"verification_evidence":evidence_ref,"evaluation":note.strip()},summary="Treatment delivery verified by the business owner; no risk score was automatically changed.")

def cancel(db,plan,note,actor):
    authorize(db,plan,actor)
    if plan.status in ("COMPLETED","CANCELLED") or not authored([note]): raise ProofError("note","Cancel an active plan with an authored reason.")
    before=plan.status
    plan.status,plan.verification_note,plan.closed_by="CANCELLED",note.strip(),actor.username
    audit_trail.record_change(db,actor=actor,action=AuditAction.TREATMENT_PLAN_CLOSED,record_type="TREATMENT_PLAN",record_ref=plan.plan_ref,before={"status":before},after={"status":plan.status,"reason":note.strip()},summary="Treatment plan cancelled by an authorized business owner; historical commitments retained.")
