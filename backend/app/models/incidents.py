"""Reported events retain their triage and response decisions."""

from datetime import date

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        CheckConstraint("reported_on >= occurred_on", name="ck_event_dates"),
        CheckConstraint(
            "status IN ('REPORTED','DISMISSED','INCIDENT','CONTAINED','RECOVERED','CLOSED')",
            name="ck_event_status",
        ),
        CheckConstraint(
            "severity IN ('UNASSESSED','LOW','MEDIUM','HIGH','CRITICAL')", name="ck_event_severity"
        ),
        CheckConstraint(
            "length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(description))>0",
            name="ck_event_required",
        ),
        CheckConstraint(
            "status NOT IN ('INCIDENT','CONTAINED','RECOVERED','CLOSED') OR (severity != 'UNASSESSED' AND length(trim(classification_note))>0)",
            name="ck_event_triage",
        ),
        CheckConstraint(
            "status != 'CLOSED' OR (closed_on IS NOT NULL AND closed_on >= reported_on AND evidence_id IS NOT NULL AND length(trim(lessons))>0 AND length(trim(closure_note))>0)",
            name="ck_event_closure",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    event_ref: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    occurred_on: Mapped[date] = mapped_column(Date)
    reported_on: Mapped[date] = mapped_column(Date)
    reporter: Mapped[str] = mapped_column(String(64))
    owner: Mapped[str] = mapped_column(String(160))
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="RESTRICT"))
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="RESTRICT"))
    finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_findings.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="REPORTED")
    severity: Mapped[str] = mapped_column(String(16), default="UNASSESSED")
    classification_note: Mapped[str] = mapped_column(Text, default="")
    notification_decision: Mapped[str] = mapped_column(Text, default="")
    lessons: Mapped[str] = mapped_column(Text, default="")
    closure_note: Mapped[str] = mapped_column(Text, default="")
    closed_on: Mapped[date | None] = mapped_column(Date)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    revision: Mapped[int] = mapped_column(default=1)


class IncidentEntry(Base):
    __tablename__ = "incident_entries"
    __table_args__ = (
        CheckConstraint(
            "length(trim(note))>0 AND length(trim(actor))>0", name="ck_incident_entry_required"
        ),
        CheckConstraint(
            "kind IN ('TRIAGE','RESPONSE','COMMUNICATION','EVIDENCE','CONTAINED','RECOVERED','CLOSED','REOPENED')",
            name="ck_incident_entry_kind",
        ),
        CheckConstraint(
            "kind != 'EVIDENCE' OR (attachment_id IS NOT NULL AND length(trim(custody_note))>0)",
            name="ck_incident_custody",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("security_events.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(24))
    occurred_on: Mapped[date] = mapped_column(Date)
    actor: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text)
    attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_attachments.id", ondelete="RESTRICT")
    )
    custody_note: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSON)
