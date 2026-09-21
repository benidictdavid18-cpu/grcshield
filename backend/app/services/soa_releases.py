"""Release approval does not turn the mutable working register into signed history."""
import hashlib
import json
from datetime import datetime,timezone
from sqlalchemy import select
from app.core import clock
from app.models.soa import SoAEntry,ImplementationStatus
from app.models.soa_release import SoARelease
from app.models.attachment import EvidenceAttachment
from app.models.framework import FrameworkControl
from app.models.audit_trail import AuditAction
from app.services import audit_trail,acceptance
from app.services.context import authored
from app.services.provenance import ProofError
from app.services.soa_validation import entry_errors,ValidationError

FIELDS=("control_ref","control_title","theme","applicable","justification_inclusion","justification_exclusion","implementation_status","implementation_description","owner","last_reviewed","next_review")

def active_gap_errors(entry):
    if entry.is_gap and not any(x.is_open and x.owner.strip() and x.due_date for x in entry.linked_remediation):
        return [ValidationError("linked_remediation_ids","An open implementation gap requires active remediation; completed or cancelled work cannot cover it.")]
    return []

def digest(entries): return hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()

def capture(db):
    rows=db.scalars(select(SoAEntry).order_by(SoAEntry.control_ref)).all()
    entries=[]
    artifacts={}
    for a in db.scalars(select(EvidenceAttachment).where(EvidenceAttachment.purged_on.is_(None))):
        artifacts.setdefault(a.evidence_id,[]).append({"id":a.id,"version":a.version,"sha256":a.sha256})
    warnings=[]
    for row in rows:
        record=audit_trail.snapshot(row,FIELDS)
        record["controls"]=[x.control_id for x in row.linked_controls]
        record["risks"]=[x.risk_ref for x in row.linked_risks]
        record["remediation"]=[audit_trail.snapshot(x,("remediation_ref","owner","due_date","status")) for x in row.linked_remediation]
        record["evidence"]=[]
        for e in row.linked_evidence:
            record["evidence"].append({**audit_trail.snapshot(e,("evidence_ref","title","valid_from","valid_until","file_reference")),"attachments":sorted(artifacts.get(e.id,[]),key=lambda x:x["id"])})
            if not artifacts.get(e.id): warnings.append(f"{e.evidence_ref}: no retrievable attachment")
            if e.is_expired(clock.today()): warnings.append(f"{e.evidence_ref}: expired for current reliance")
        entries.append(record)
    return entries,sorted(set(warnings))

def create(db,payload,actor):
    if not payload.version.strip() or not payload.change_note.strip(): raise ProofError("change_note","A version and change rationale are required.")
    if db.scalar(select(SoARelease.id).where(SoARelease.version==payload.version)):
        raise ProofError("version","This release version is already retained.")
    entries,warnings=capture(db)
    from app.seed.annex_a_2022 import ANNEX_A_CONTROLS
    if {e["control_ref"] for e in entries}!={c.ref for c in ANNEX_A_CONTROLS} or len(entries)!=93:
        raise ProofError("entries","A release must contain the exact 93 Annex A:2022 controls.")
    row=SoARelease(version=payload.version,status="DRAFT",entries=entries,entry_count=93,content_digest=digest(entries),change_note=payload.change_note,prepared_by=actor.username,evidence_warnings=warnings,evidence_limitations_acknowledged=False)
    db.add(row)
    audit_trail.record_change(db,actor=actor,action=AuditAction.SOA_RELEASE_RECORDED,record_type="SOA_RELEASE",record_ref=row.version,before=None,after={"digest":row.content_digest,"entry_count":93,"change_note":row.change_note,"evidence_warnings":warnings},summary="Draft SoA release captures the exact applicability statements and supporting references.")
    return row

def approve(db,row,payload,actor):
    if not acceptance.authority(db,actor,"Chief Executive Officer"):
        raise PermissionError("Current Chief Executive Officer approval authority is required for SoA sign-off.")
    if row.status!="DRAFT" or not authored([row.change_note,payload.note]):
        raise ProofError("note","Approve an unapproved release with authored change and approval notes.")
    current,warnings=capture(db)
    if digest(row.entries)!=row.content_digest or digest(current)!=row.content_digest:
        raise ProofError("entries","The working copy changed or snapshot integrity failed; prepare a new release.")
    for entry in db.scalars(select(SoAEntry)):
        errors=entry_errors(entry)+active_gap_errors(entry)
        if errors: raise ProofError(errors[0].field,f"{entry.control_ref}: {errors[0].message}")
        if "TODO AUTHOR:BENNY" in json.dumps(audit_trail.snapshot(entry,FIELDS)):
            raise ProofError("entries",f"{entry.control_ref} has an unresolved author judgment.")
        if entry.applicable and entry.implementation_status==ImplementationStatus.IMPLEMENTED and not entry.linked_evidence:
            raise ProofError("evidence",f"{entry.control_ref} claims implementation without any evidence reference.")
    if warnings and not payload.acknowledge_evidence_limitations:
        raise ProofError("acknowledge_evidence_limitations","Review and explicitly acknowledge the listed evidence availability/freshness limitations; approval does not certify control effectiveness.")
    row.status,row.approved_by,row.approved_at,row.approval_note="APPROVED",actor.username,datetime.now(timezone.utc),payload.note.strip()
    row.evidence_warnings=warnings
    row.evidence_limitations_acknowledged=payload.acknowledge_evidence_limitations
    # The latest signed applicability decision governs the operational crosswalk.
    catalogue={c.control_ref:c for c in db.scalars(select(FrameworkControl).where(FrameworkControl.control_ref.like("A.%")))}
    for entry in row.entries:
        catalogue[entry["control_ref"]].in_scope=entry["applicable"]
    audit_trail.record_change(db,actor=actor,action=AuditAction.SOA_RELEASE_APPROVED,record_type="SOA_RELEASE",record_ref=row.version,before={"status":"DRAFT"},after={"status":row.status,"digest":row.content_digest,"approved_by":row.approved_by,"approval_note":row.approval_note,"evidence_warnings":warnings,"limitations_acknowledged":row.evidence_limitations_acknowledged},summary="Authorized management sign-off on the retained SoA snapshot; crosswalk scope follows this release.")
    return row

def state(db):
    latest=db.scalar(select(SoARelease).where(SoARelease.status=="APPROVED").order_by(SoARelease.approved_at.desc(),SoARelease.id.desc()).limit(1))
    entries,_=capture(db)
    return {"approval_state":"APPROVED" if latest and latest.content_digest==digest(entries) else "WORKING_DRAFT", "approved_release_version":latest.version if latest else None,"has_unreleased_changes":latest is None or latest.content_digest!=digest(entries)}

def diff(before,after):
    a={x["control_ref"]:x for x in before}
    b={x["control_ref"]:x for x in after}
    return [{"control_ref":ref,"before":a.get(ref),"after":b.get(ref),"changed_fields":sorted(k for k in set(a.get(ref,{}) or {})|set(b.get(ref,{}) or {}) if a.get(ref,{}).get(k)!=b.get(ref,{}).get(k))} for ref in sorted(set(a)|set(b)) if a.get(ref)!=b.get(ref)]
