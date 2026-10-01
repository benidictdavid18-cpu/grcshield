"""Approval is tied to actual content; publication never destroys an older revision."""

import hashlib

from sqlalchemy import select

from app.core import clock
from app.models.audit_trail import AuditAction
from app.models.document import ControlledDocument, DocumentAcknowledgement, DocumentRevision
from app.models.soa import Evidence
from app.services import audit_trail
from app.services.context import authored
from app.services.provenance import ProofError

DOCUMENT_FIELDS = (
    "title",
    "owner",
    "classification",
    "source_kind",
    "external_source",
    "distribution",
    "review_date",
)
REVISION_FIELDS = (
    "id",
    "version",
    "content_digest",
    "status",
    "approved_by",
    "approved_on",
    "approval_note",
    "published_on",
    "withdrawal_note",
)


def digest(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def save(db, ref, payload, actor):
    if (
        not ref.strip()
        or len(ref) > 32
        or not all(getattr(payload, f).strip() for f in ("title", "owner", "distribution"))
    ):
        raise ProofError(
            "document_ref",
            "Reference, title, owner and distribution must not be blank; reference is at most 32 characters.",
        )
    if payload.source_kind == "EXTERNAL" and not (payload.external_source or "").strip():
        raise ProofError(
            "external_source",
            "Identify the controlled external source and its version or publication.",
        )
    row = db.scalar(
        select(ControlledDocument).where(ControlledDocument.document_ref == ref).with_for_update()
    )
    before = audit_trail.snapshot(row, DOCUMENT_FIELDS) if row else None
    if row is None:
        row = ControlledDocument(document_ref=ref)
        db.add(row)
    for name in DOCUMENT_FIELDS:
        setattr(row, name, getattr(payload, name))
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.DOCUMENT_UPDATED,
        record_type="DOCUMENT",
        record_ref=ref,
        before=before,
        after=audit_trail.snapshot(row, DOCUMENT_FIELDS),
        summary="Controlled document ownership, review and distribution recorded.",
    )
    return row


def create_revision(db, document, payload, actor):
    if not all(getattr(payload, f).strip() for f in ("version", "content", "change_note")):
        raise ProofError("content", "Version, retrievable content and a change note are required.")
    if db.scalar(
        select(DocumentRevision.id).where(
            DocumentRevision.document_id == document.id, DocumentRevision.version == payload.version
        )
    ):
        raise ProofError("version", "This version is already retained; use a new version.")
    evidence = (
        db.scalar(select(Evidence).where(Evidence.evidence_ref == payload.evidence_ref))
        if payload.evidence_ref
        else None
    )
    if payload.evidence_ref and evidence is None:
        raise ProofError("evidence_ref", "Unknown evidence reference.")
    row = DocumentRevision(
        document_id=document.id,
        version=payload.version,
        content=payload.content,
        content_digest=digest(payload.content),
        change_note=payload.change_note,
        evidence_id=evidence.id if evidence else None,
        author=actor.username,
        status="DRAFT",
    )
    db.add(row)
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.DOCUMENT_REVISION_RECORDED,
        record_type="DOCUMENT",
        record_ref=document.document_ref,
        before=None,
        after={
            "version": row.version,
            "content_digest": row.content_digest,
            "change_note": row.change_note,
            "evidence_ref": payload.evidence_ref,
        },
        summary="A retained document revision was authored; it is not yet approved or published.",
    )
    return row


def transition(db, row, action, note, actor):
    document = db.scalar(
        select(ControlledDocument).where(ControlledDocument.id == row.document_id).with_for_update()
    )
    before = audit_trail.snapshot(row, REVISION_FIELDS)
    if digest(row.content) != row.content_digest:
        raise ProofError("content", "Stored content no longer matches its recorded digest.")
    if action == "approve":
        if (
            row.status != "DRAFT"
            or not authored(
                [row.content, row.change_note, note, document.owner, document.distribution]
            )
            or document.review_date <= clock.today()
        ):
            raise ProofError(
                "note",
                "Approval requires a draft, completed author decisions and a future review date.",
            )
        row.status, row.approved_by, row.approved_on, row.approval_note = (
            "APPROVED",
            actor.username,
            clock.today(),
            note.strip(),
        )
    elif action == "publish":
        if row.status != "APPROVED" or document.review_date <= clock.today():
            raise ProofError(
                "status",
                "Only an approved revision with a current review schedule can be published.",
            )
        current = db.scalars(
            select(DocumentRevision).where(
                DocumentRevision.document_id == document.id, DocumentRevision.status == "PUBLISHED"
            )
        ).all()
        for old in current:
            old.status = "SUPERSEDED"
        db.flush()
        row.status, row.published_on = "PUBLISHED", clock.today()
    elif action == "withdraw":
        if row.status != "PUBLISHED" or not authored([note]):
            raise ProofError(
                "note", "Withdrawal requires a published revision and an authored reason."
            )
        row.status, row.withdrawal_note = "WITHDRAWN", note.strip()
    else:
        raise ProofError("action", "Choose approve, publish or withdraw.")
    audit_trail.record_change(
        db,
        actor=actor,
        action=AuditAction.DOCUMENT_LIFECYCLE_CHANGED,
        record_type="DOCUMENT",
        record_ref=document.document_ref,
        before=before,
        after=audit_trail.snapshot(row, REVISION_FIELDS),
        summary=f"Document revision {row.version}: {action}. Prior content remains retrievable.",
    )
    return row


def acknowledge(db, row, actor):
    if row.status != "PUBLISHED":
        raise ProofError("revision_id", "Acknowledge the currently published revision.")
    existing = db.scalar(
        select(DocumentAcknowledgement).where(
            DocumentAcknowledgement.revision_id == row.id,
            DocumentAcknowledgement.username == actor.username,
        )
    )
    if existing is None:
        existing = DocumentAcknowledgement(revision_id=row.id, username=actor.username)
        db.add(existing)
    return existing
