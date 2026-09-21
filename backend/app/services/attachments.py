"""Store exact bytes, refuse unsafe names, and never manufacture missing evidence."""
import base64
import binascii
import hashlib
import json
from sqlalchemy import select
from app.core import clock
from app.models.attachment import EvidenceAttachment
from app.models.audit_trail import AuditAction
from app.models.user import Role
from app.services import audit_trail
from app.services.context import authored
from app.services.provenance import ProofError

MAX_BYTES=8*1024*1024
FIELDS=("id","evidence_id","version","filename","content_type","byte_size","sha256","source","access_scope","retention_until","retention_reason","legal_hold","purged_on","purged_by","purge_reason")

def can_read(row,user): return row.access_scope=="REGISTER_READERS" or user.can_write

def store(db,evidence,payload,actor):
    if any(c in payload.filename for c in ('/','\\')) or payload.filename in ('.','..') or any(ord(c)<32 for c in payload.filename):
        raise ProofError("filename","Supply a filename without paths or control characters.")
    if not authored([payload.source,payload.retention_reason]) or not payload.version.strip() or not payload.filename.strip():
        raise ProofError("source","Record an authored source and retention reason, and a nonblank filename/version.")
    if payload.retention_until<clock.today():
        raise ProofError("retention_until","Retention cannot end before this upload date.")
    if db.scalar(select(EvidenceAttachment.id).where(EvidenceAttachment.evidence_id==evidence.id,EvidenceAttachment.version==payload.version)):
        raise ProofError("version","This attachment version is already retained; use another version.")
    try: data=base64.b64decode(payload.content_base64,validate=True)
    except (ValueError,binascii.Error) as e: raise ProofError("content_base64","Invalid base64 file content.") from e
    if not 0<len(data)<=MAX_BYTES:
        raise ProofError("content_base64","Attachment must contain between one byte and 8 MiB.")
    signatures={"application/pdf":b"%PDF-","image/png":b"\x89PNG\r\n\x1a\n","image/jpeg":b"\xff\xd8\xff"}
    if payload.content_type in signatures and not data.startswith(signatures[payload.content_type]):
        raise ProofError("content_type","File signature does not match the declared type.")
    if payload.content_type in ("text/plain","text/csv","application/json"):
        try:
            decoded=data.decode("utf-8")
            if "\x00" in decoded: raise ValueError("NUL in text")
            if payload.content_type=="application/json": json.loads(decoded)
        except (UnicodeError,ValueError) as e: raise ProofError("content_type","Text must be UTF-8; JSON must parse successfully.") from e
    row=EvidenceAttachment(evidence_id=evidence.id,version=payload.version,filename=payload.filename,content_type=payload.content_type,
        byte_size=len(data),sha256=hashlib.sha256(data).hexdigest(),content_data=data,source=payload.source,uploaded_by=actor.username,uploaded_on=clock.today(),
        access_scope=payload.access_scope,retention_until=payload.retention_until,retention_reason=payload.retention_reason,legal_hold=payload.legal_hold)
    db.add(row)
    db.flush()
    audit_trail.record_change(db,actor=actor,action=AuditAction.EVIDENCE_ATTACHED,record_type="EVIDENCE",record_ref=evidence.evidence_ref,before=None,after=audit_trail.snapshot(row,FIELDS),summary="Exact evidence bytes retained with checksum, provenance and retention; no effectiveness judgment was made.")
    return row

def download(db,row,actor):
    if not can_read(row,actor): raise PermissionError("This attachment is restricted to register maintainers.")
    if row.purged_on is not None: raise ProofError("attachment_id","The retention-controlled content was purged; its metadata remains.")
    data=row.content_data
    if data is None or hashlib.sha256(data).hexdigest()!=row.sha256 or len(data)!=row.byte_size:
        raise ProofError("content","Artifact integrity check failed; contact the evidence owner.")
    audit_trail.record_change(db,actor=actor,action=AuditAction.EVIDENCE_DOWNLOADED,record_type="EVIDENCE_ATTACHMENT",record_ref=str(row.id),before=None,after={"sha256":row.sha256,"byte_size":row.byte_size},summary="Authenticated retrieval of a retained evidence artifact.")
    return data

def retention(db,row,payload,actor):
    if actor.role!=Role.ADMIN: raise PermissionError("Administrator role required to change artifact retention or legal hold.")
    if row.purged_on is not None or payload.retention_until<row.retention_until or not authored([payload.reason]):
        raise ProofError("retention_until","Retained content needs an authored reason; retention can be extended, not shortened.")
    before=audit_trail.snapshot(row,FIELDS)
    row.retention_until,row.legal_hold=payload.retention_until,payload.legal_hold
    row.retention_reason=payload.reason.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.EVIDENCE_RETENTION_CHANGED,record_type="EVIDENCE_ATTACHMENT",record_ref=str(row.id),before=before,after=audit_trail.snapshot(row,FIELDS),summary="Artifact retention or legal hold changed by an administrator.")

def purge(db,row,reason,actor):
    if actor.role!=Role.ADMIN: raise PermissionError("Administrator role required to purge retained evidence.")
    if row.purged_on is not None or row.legal_hold or clock.today()<row.retention_until or not authored([reason]):
        raise ProofError("purge_reason","Purge requires elapsed retention, no legal hold and an authored reason.")
    before=audit_trail.snapshot(row,FIELDS)
    row.content_data=None
    row.purged_on,row.purged_by,row.purge_reason=clock.today(),actor.username,reason.strip()
    audit_trail.record_change(db,actor=actor,action=AuditAction.EVIDENCE_PURGED,record_type="EVIDENCE_ATTACHMENT",record_ref=str(row.id),before=before,after=audit_trail.snapshot(row,FIELDS),summary="Retained artifact bytes purged after the retention period; metadata and checksum preserved.")
