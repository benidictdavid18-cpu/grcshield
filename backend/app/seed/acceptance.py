"""Preserve authored fictional decisions; never invent an authenticated signer."""
from sqlalchemy import select

from app.models.acceptance import AcceptanceDecision
from app.services.acceptance import digest


def seed_decisions(db, exceptions):
    for row in exceptions.values():
        if row.status.value == "PENDING" or db.scalar(select(AcceptanceDecision.id).where(AcceptanceDecision.exception_id == row.id)) is not None:
            continue
        db.add(AcceptanceDecision(exception_id=row.id, record_digest=digest(row), decision=row.status.value, source="SAMPLE_AUTHORED",
            actor=row.approver_role, business_role=row.approver_role,
            note=row.decision_note or row.business_justification,
            approval_date=row.approval_date, expiry_date=row.expiry_date))
    db.flush()
