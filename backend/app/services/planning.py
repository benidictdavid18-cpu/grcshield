"""Leadership commits targets and resources; observations retain the author's evaluation."""
from datetime import datetime,timezone
from sqlalchemy import select
from app.core import clock
from app.models.planning import ISMSPlan,PlanEvaluation
from app.models.context import ContextEntry
from app.models.risk import Risk
from app.models.kri import KriDefinition
from app.models.soa import Evidence
from app.models.audit_trail import AuditAction
from app.services import audit_trail,acceptance
from app.services.context import authored,FIELDS as CONTEXT_FIELDS
from app.services.provenance import ProofError

FIELDS=("plan_ref","kind","title","owner","resources","rationale","context_id","risk_id","kri_id","due_date","measure_definition","target_value","direction","impact_assessment","rollback_plan","status","revision")

def lookup(db,model,column,ref,field):
    if ref is None: return None
    row=db.scalar(select(model).where(column==ref))
    if row is None: raise ProofError(field,"The linked record must exist.")
    return row

def save(db,ref,payload,actor):
    if not ref.strip() or len(ref)>32 or not all(getattr(payload,x).strip() for x in ("title","owner","resources","rationale")):
        raise ProofError("plan_ref","Reference, owner, resources, title and rationale are required.")
    context=lookup(db,ContextEntry,ContextEntry.context_ref,payload.context_ref,"context_ref")
    risk=lookup(db,Risk,Risk.risk_ref,payload.risk_ref,"risk_ref")
    kri=lookup(db,KriDefinition,KriDefinition.kri_ref,payload.kri_ref,"kri_ref")
    row=db.scalar(select(ISMSPlan).where(ISMSPlan.plan_ref==ref).with_for_update())
    before=audit_trail.snapshot(row,FIELDS) if row else None
    if row and (row.status!="DRAFT" or row.revision!=payload.expected_revision):
        raise ProofError("expected_revision","Edit only the current draft; retain approved commitments and create a new version.")
    if row is None:
        row=ISMSPlan(plan_ref=ref,revision=0,status="DRAFT")
        db.add(row)
    for field in ("kind","title","owner","resources","rationale","due_date","measure_definition","target_value","direction","impact_assessment","rollback_plan"):
        setattr(row,field,getattr(payload,field))
    row.context_id,row.risk_id,row.kri_id=context.id,risk.id if risk else None,kri.id if kri else None
    row.revision+=1
    audit_trail.record_change(db,actor=actor,action=AuditAction.ISMS_PLAN_UPDATED,record_type="ISMS_PLAN",record_ref=ref,before=before,after=audit_trail.snapshot(row,FIELDS),summary="Draft objective or planned ISMS change recorded with its context and resources.")
    return row

def authority(db,actor):
    if not acceptance.authority(db,actor,"Chief Executive Officer"):
        raise PermissionError("Current CEO business authority is required to approve or cancel ISMS commitments.")

def approve(db,row,note,actor):
    authority(db,actor)
    context=db.get(ContextEntry,row.context_id)
    required=[row.title,row.owner,row.resources,row.rationale,note]
    if row.kind=="OBJECTIVE": required += [row.measure_definition or "",row.direction or ""]
    else: required += [row.impact_assessment or "",row.rollback_plan or ""]
    if row.status!="DRAFT" or not authored(required) or row.due_date is None or row.due_date<=clock.today():
        raise ProofError("note","Approve a complete draft with authored resources, criteria and a future target date.")
    if row.kind=="OBJECTIVE" and row.target_value is None:
        raise ProofError("target_value","An objective needs an explicit measurable target.")
    if context.status!="REVIEWED" or context.review_date<=clock.today():
        raise ProofError("context_ref","Review the source context before committing this plan.")
    row.approved_snapshot={**audit_trail.snapshot(row,FIELDS),"context":audit_trail.snapshot(context,CONTEXT_FIELDS)}
    row.status,row.approved_by,row.approved_at,row.approval_note="APPROVED",actor.username,datetime.now(timezone.utc),note.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.ISMS_PLAN_APPROVED,record_type="ISMS_PLAN",record_ref=row.plan_ref,before={"status":"DRAFT"},after={"status":row.status,"snapshot":row.approved_snapshot,"note":row.approval_note},summary="Leadership approved the stated objective or management-system change and its resources.")

def implement(db,row,payload,actor):
    evidence=lookup(db,Evidence,Evidence.evidence_ref,payload.evidence_ref,"evidence_ref")
    if row.kind!="CHANGE" or row.status!="APPROVED" or payload.implemented_on>clock.today() or not authored([payload.note]):
        raise ProofError("note","Record implementation of an approved change with real evidence, an actual date and an authored note.")
    row.status,row.implementation_date,row.implementation_evidence_id,row.implementation_note="IMPLEMENTED",payload.implemented_on,evidence.id,payload.note.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.ISMS_CHANGE_IMPLEMENTED,record_type="ISMS_PLAN",record_ref=row.plan_ref,before={"status":"APPROVED"},after={"status":row.status,"implemented_on":row.implementation_date,"evidence_ref":payload.evidence_ref,"note":row.implementation_note},summary="Implementation recorded separately from evaluating the change's outcome.")

def evaluate(db,row,payload,actor):
    evidence=lookup(db,Evidence,Evidence.evidence_ref,payload.evidence_ref,"evidence_ref")
    allowed=("APPROVED","EVALUATED") if row.kind=="OBJECTIVE" else ("IMPLEMENTED","EVALUATED")
    if row.status not in allowed or not authored([payload.evaluation_note]) or payload.observed_on>clock.today():
        raise ProofError("evaluation_note","Evaluate an approved objective or implemented change using dated evidence and an authored assessment.")
    if row.kind=="OBJECTIVE" and payload.observed_value is None:
        raise ProofError("observed_value","Record the observed value for this measurable objective.")
    if row.kind=="CHANGE" and payload.observed_on<row.implementation_date:
        raise ProofError("observed_on","Evaluate a change after its recorded implementation.")
    evaluation=PlanEvaluation(plan_id=row.id,observed_on=payload.observed_on,observed_value=payload.observed_value,evaluation_note=payload.evaluation_note.strip(),evidence_id=evidence.id,actor=actor.username)
    db.add(evaluation)
    row.status="EVALUATED"
    audit_trail.record_change(db,actor=actor,action=AuditAction.ISMS_PLAN_EVALUATED,record_type="ISMS_PLAN",record_ref=row.plan_ref,before=None,after={"observed_on":payload.observed_on,"observed_value":payload.observed_value,"evidence_ref":payload.evidence_ref,"evaluation":payload.evaluation_note},summary="Observed results and the human evaluation retained; no automatic assertion of success.")
    return evaluation

def cancel(db,row,note,actor):
    authority(db,actor)
    if row.status=="CANCELLED" or not authored([note]): raise ProofError("note","An authored cancellation reason is required.")
    before=row.status
    row.status,row.cancellation_note="CANCELLED",note.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.ISMS_PLAN_UPDATED,record_type="ISMS_PLAN",record_ref=row.plan_ref,before={"status":before},after={"status":row.status,"reason":row.cancellation_note},summary="Leadership cancelled the commitment without deleting its history.")
