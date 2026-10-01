"""A reported observation from TEST-008 is not a declared breach."""

from datetime import date

from sqlalchemy import select

from app.models.audit import AuditFinding
from app.models.incidents import SecurityEvent
from app.models.risk import Control, Risk

INCIDENT_HINT = "TODO AUTHOR:BENNY - assess classification, severity and notification obligations from the source workpaper; a failed control does not establish a reportable breach."


def seed_incidents(db):
    if db.scalar(select(SecurityEvent.id).where(SecurityEvent.event_ref == "EVT-001")):
        return
    risk = db.scalar(select(Risk).where(Risk.risk_ref == "RISK-008"))
    control = db.scalar(select(Control).where(Control.control_id == "DP-005"))
    finding = db.scalar(select(AuditFinding).where(AuditFinding.finding_ref == "FIND-003"))
    if not all((risk, control, finding)):
        return
    db.add(
        SecurityEvent(
            event_ref="EVT-001",
            title="Reported masking-scope observation",
            description="Sample / Portfolio Assessment. TEST-008 reports unmasked data in two non-production stores. "
            + INCIDENT_HINT,
            source="TEST-008 / FIND-003; sample observation awaiting event triage.",
            occurred_on=date(2026, 7, 24),
            reported_on=date(2026, 7, 24),
            reporter="sample.author",
            owner="TODO AUTHOR:BENNY - appoint the response owner.",
            risk_id=risk.id,
            control_id=control.id,
            finding_id=finding.id,
            status="REPORTED",
            severity="UNASSESSED",
            classification_note=INCIDENT_HINT,
            notification_decision=INCIDENT_HINT,
        )
    )
    db.flush()
