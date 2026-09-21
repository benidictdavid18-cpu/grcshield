"""Context review makes judgments explicit; scope approval freezes its inputs."""
from sqlalchemy import select
from app.core import clock
from app.models.context import ContextEntry, ScopeRevision
from app.models.risk import Risk
from app.models.audit_trail import AuditAction
from app.services import audit_trail
from app.services.provenance import ProofError

FIELDS=("context_ref","kind","topic","title","statement","source","owner","review_date","relevance","decision_note","risk_id","revision","status","reviewed_by","reviewed_on")

def authored(values):
    return all(str(v).strip() and "TODO AUTHOR:BENNY" not in str(v) for v in values)

def save_context(db, ref, payload, actor):
    if not ref.strip() or len(ref)>32:
        raise ProofError("context_ref","Use a nonblank reference of at most 32 characters.")
    row=db.scalar(select(ContextEntry).where(ContextEntry.context_ref==ref).with_for_update())
    if row and payload.expected_revision != row.revision:
        raise ProofError("expected_revision","The record changed; reload it and submit its current revision.")
    if not all(getattr(payload,f).strip() for f in ("title","statement","source","owner","decision_note")):
        raise ProofError("statement","Title, source, owner, statement and decision note must not be blank.")
    risk=db.scalar(select(Risk).where(Risk.risk_ref==payload.risk_ref)) if payload.risk_ref else None
    if payload.risk_ref and risk is None:
        raise ProofError("risk_ref","Unknown risk reference.")
    before=audit_trail.snapshot(row,FIELDS) if row else None
    if row is None:
        row=ContextEntry(context_ref=ref,revision=0)
        db.add(row)
    for field in ("kind","topic","title","statement","source","owner","review_date","relevance","decision_note"):
        setattr(row,field,getattr(payload,field))
    row.risk_id=risk.id if risk else None
    row.revision+=1
    row.status,row.reviewed_by,row.reviewed_on="DRAFT",None,None
    audit_trail.record_change(db,actor=actor,action=AuditAction.CONTEXT_UPDATED,record_type="ISMS_CONTEXT",record_ref=ref,before=before,after=audit_trail.snapshot(row,FIELDS),summary="Context input revised; review is required for the changed judgment.")
    return row

def review_context(db,row,actor):
    if row.status == "REVIEWED":
        raise ProofError("status","This revision is already reviewed.")
    if row.relevance=="UNASSESSED" or not authored([row.title,row.statement,row.source,row.owner,row.decision_note]):
        raise ProofError("decision_note","Resolve the relevance decision and all author hints before review.")
    if row.review_date<=clock.today():
        raise ProofError("review_date","Set the next review after the current assessment date.")
    before=audit_trail.snapshot(row,FIELDS)
    row.status,row.reviewed_by,row.reviewed_on="REVIEWED",actor.username,clock.today()
    audit_trail.record_change(db,actor=actor,action=AuditAction.CONTEXT_REVIEWED,record_type="ISMS_CONTEXT",record_ref=row.context_ref,before=before,after=audit_trail.snapshot(row,FIELDS),summary="An authenticated author reviewed the context decision.")
    return row

def create_scope(db,payload,actor):
    if db.scalar(select(ScopeRevision.id).where(ScopeRevision.version==payload.version)):
        raise ProofError("version","This scope version already exists; create a new version.")
    if not all(getattr(payload,f).strip() for f in ("version","statement","interfaces","exclusions","owner")):
        raise ProofError("statement","Scope, interfaces, exclusions and owner must not be blank.")
    refs=set(payload.context_refs)
    rows=db.scalars(select(ContextEntry).where(ContextEntry.context_ref.in_(refs)).order_by(ContextEntry.context_ref)).all()
    if {x.context_ref for x in rows}!=refs:
        raise ProofError("context_refs","Every context reference must exist.")
    row=ScopeRevision(**payload.model_dump(exclude={"context_refs"}),status="DRAFT",context_snapshot=[audit_trail.snapshot(x,FIELDS) for x in rows])
    db.add(row)
    audit_trail.record_change(db,actor=actor,action=AuditAction.SCOPE_RECORDED,record_type="ISMS_SCOPE",record_ref=payload.version,before=None,after={**payload.model_dump(),"context_snapshot":row.context_snapshot},summary="A draft scope revision retains its selected context inputs.")
    return row

def approve_scope(db,row,note,actor):
    if row.status != "DRAFT":
        raise ProofError("status","Approved scope revisions are immutable; create a new version.")
    if not authored([note,row.statement,row.interfaces,row.exclusions,row.owner]):
        raise ProofError("note","Resolve author hints and record an approval note.")
    if row.review_date<=clock.today():
        raise ProofError("review_date","Set a future scope review date.")
    snapshot=row.context_snapshot
    if not {"ISSUE","PARTY_REQUIREMENT","PROCESS"} <= {x["kind"] for x in snapshot} or not any(x["topic"]=="CLIMATE" for x in snapshot):
        raise ProofError("context_refs","Scope needs reviewed issues, party requirements, processes and a climate-relevance determination.")
    for item in snapshot:
        current=db.scalar(select(ContextEntry).where(ContextEntry.context_ref==item["context_ref"]))
        if current is None or current.status!="REVIEWED" or current.review_date<=clock.today() or audit_trail.snapshot(current,FIELDS)!=item:
            raise ProofError("context_refs","A context input is stale or unreviewed; create a fresh scope draft after review.")
    row.status,row.approved_by,row.approved_on,row.approval_note="APPROVED",actor.username,clock.today(),note.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.SCOPE_APPROVED,record_type="ISMS_SCOPE",record_ref=row.version,before={"status":"DRAFT"},after={"status":row.status,"approved_by":row.approved_by,"approved_on":row.approved_on,"note":row.approval_note,"context_snapshot":snapshot},summary="Scope approved against a frozen set of reviewed context decisions.")
    return row
