"""Attributable approval supplements, rather than rewrites, acceptance validators."""
import hashlib
import json
from sqlalchemy import select
from sqlalchemy.orm import object_session
from app.core import clock
from app.models.acceptance import AcceptanceAuthority, AcceptanceDecision
from app.models.audit_trail import AuditAction
from app.models.user import Role
from app.services.privacy_continuity import ExceptionStatus, exception_state, validate_exception
from app.services import audit_trail
from app.services.provenance import ProofError


def latest(row):
    db = object_session(row)
    return db.scalar(select(AcceptanceDecision).where(AcceptanceDecision.exception_id == row.id).order_by(AcceptanceDecision.id.desc()).limit(1)) if db else None

def digest(row):
    payload = audit_trail.snapshot(row, ("risk_id", "requested_by", "business_justification", "compensating_controls", "approver_role", "approval_date", "expiry_date", "review_trigger", "status", "decision_note"))
    payload["residual"] = [row.risk.residual_likelihood, row.risk.residual_impact]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def verified(row):
    signed = latest(row)
    return bool(signed and signed.record_digest == digest(row) and signed.decision == row.status.value and signed.business_role == row.approver_role and signed.approval_date == row.approval_date and signed.expiry_date == row.expiry_date)

def effective_state(row, as_of):
    if row.status == ExceptionStatus.PENDING:
        return "PENDING"
    if not verified(row):
        return "UNVERIFIED"
    if row.status == ExceptionStatus.APPROVED and row.approval_date and row.approval_date > as_of:
        return "NOT_YET_EFFECTIVE"
    return exception_state(row.expiry_date, row.status, as_of)

def covers(row, as_of):
    return row.status == ExceptionStatus.APPROVED and row.approval_date is not None and row.approval_date <= as_of <= row.expiry_date and verified(row)

def authority(db, user, role):
    return db.scalar(select(AcceptanceAuthority).where(AcceptanceAuthority.user_id == user.id, AcceptanceAuthority.business_role == role, AcceptanceAuthority.expires_on >= clock.today()))

def grant(db, actor, user, business_role, expires_on, reason):
    if actor.role != Role.ADMIN:
        raise PermissionError("Only an administrator can bind a business approval role to an account.")
    if not user.can_write or not user.is_active:
        raise ProofError("username", "The approver must be an active account with write access.")
    if not reason.strip() or "TODO AUTHOR:BENNY" in reason or expires_on <= clock.today():
        raise ProofError("grant_reason", "An authored grant reason and future expiry are required.")
    row = db.scalar(select(AcceptanceAuthority).where(AcceptanceAuthority.user_id == user.id, AcceptanceAuthority.business_role == business_role))
    before = audit_trail.snapshot(row, ("business_role", "expires_on", "grant_reason")) if row else None
    if row is None:
        row = AcceptanceAuthority(user_id=user.id, business_role=business_role)
        db.add(row)
    row.expires_on, row.grant_reason, row.granted_by = expires_on, reason.strip(), actor.username
    audit_trail.record_change(db, actor=actor, action=AuditAction.ACCEPTANCE_AUTHORITY_GRANTED,
        record_type="USER",record_ref=user.username,before=before,
        after={"business_role":business_role,"expires_on":expires_on,"reason":reason.strip()},summary="Business approval authority bound to an authenticated account with expiry.")
    return row

def decide(db, row, actor, decision, note, expiry_date):
    if not authority(db, actor, row.approver_role):
        raise PermissionError("This account has no current authority for the recorded business approver role.")
    if not note.strip() or "TODO AUTHOR:BENNY" in note:
        raise ProofError("note", "An authored decision note is required.")
    if decision not in ("APPROVED", "REJECTED", "WITHDRAWN"):
        raise ProofError("decision", "Choose APPROVED, REJECTED or WITHDRAWN.")
    if decision == "REJECTED" and covers(row, clock.today()):
        raise ProofError("decision", "Withdraw an existing live acceptance rather than rejecting its original request.")
    expiry = expiry_date or row.expiry_date
    approved_on = clock.today() if decision == "APPROVED" else row.approval_date
    errors = validate_exception(approver_role=row.approver_role, risk_owner_role=row.risk.owner_role,
        expiry_date=expiry, approval_date=approved_on, business_justification=row.business_justification,
        review_trigger=row.review_trigger, status=ExceptionStatus(decision))
    if errors:
        raise ProofError(errors[0].field, errors[0].message)
    before = audit_trail.snapshot(row, ("status", "approval_date", "expiry_date", "decision_note"))
    row.status, row.approval_date, row.expiry_date, row.decision_note = ExceptionStatus(decision), approved_on, expiry, note.strip()
    signed = AcceptanceDecision(exception_id=row.id,record_digest=digest(row),decision=decision,source="AUTHENTICATED",actor=actor.username,
        business_role=row.approver_role,note=note.strip(),approval_date=approved_on,expiry_date=expiry)
    db.add(signed)
    audit_trail.record_change(db,actor=actor,action=AuditAction.ACCEPTANCE_DECIDED,record_type="RISK_EXCEPTION",record_ref=row.exception_ref,before=before,
        after={**audit_trail.snapshot(row,("status","approval_date","expiry_date","decision_note")),"business_justification":row.business_justification,"compensating_controls":row.compensating_controls,"review_trigger":row.review_trigger,"approver_role":row.approver_role},summary="An authorized business approver recorded an acceptance decision; prior decisions are retained.")
    return signed
