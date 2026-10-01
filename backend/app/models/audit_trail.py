"""The application's own audit trail: who changed which record, from what, to what.

Distinct from ``models/audit.py``, which holds the ISMS's audit programme -- internal
audits, findings, workpapers. Those are records *about* FinFlow's controls. This table is
a record about *this application*: every mutation a user makes through the API, with the
actor, the record, and the values before and after.

An ISMS content record already says who prepared it and who reviewed it. What it cannot
say is who lowered a residual score last Tuesday and what it was before, and that is the
first question an auditor asks when a number on the register has moved. SECURITY.md
named the absence of this table the most significant gap for a tool of this kind.

Design choices, and why:

- **Written in the same transaction as the change.** A change with no event, or an event
  with no change, is a trail that cannot be trusted. The service adds the row to the
  session; the route commits both together, and a 422 that rolls the change back rolls
  the event back with it.
- **Actor stored as text, not a foreign key.** Same reasoning as the AI interaction log:
  the trail must stay readable after the account is deactivated or removed, and a
  ``SET NULL`` would erase exactly the fact the trail exists to keep.
- **Records named by business reference** (RISK-004, A.8.5, TEST-013), not surrogate
  id, so a row is legible on its own and survives a re-seed.
- **``action`` is a string column, not a native enum.** Migration 0008 documents what
  adding a value to a PostgreSQL enum costs. A new kind of mutation should cost one
  line in ``AuditAction``, not a migration.
- **Before and after are JSON snapshots of the fields the endpoint may change**, not
  the whole record. Enough to reconstruct the edit; small enough to read.
- **Append-only by construction.** No endpoint updates or deletes a row, and the
  read-only auditor role can list them. Nothing at the database level prevents a DBA
  from editing the table; that is a known limit, stated in SECURITY.md.
"""

import enum

from sqlalchemy import JSON, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditAction(str, enum.Enum):
    """One value per kind of mutation the API can perform.

    Stored as plain text (see the module docstring), so adding a value here is the
    whole change.
    """

    ASSURANCE_CHANGED = "ASSURANCE_CHANGED"
    INCIDENT_CHANGED = "INCIDENT_CHANGED"
    SUPPLIER_CHANGED = "SUPPLIER_CHANGED"
    COMPETENCE_CHANGED = "COMPETENCE_CHANGED"
    OBLIGATION_CHANGED = "OBLIGATION_CHANGED"
    OPERATIONAL_CHANGED = "OPERATIONAL_CHANGED"
    MONITORING_CHANGED = "MONITORING_CHANGED"
    ACCEPTANCE_DECIDED = "ACCEPTANCE_DECIDED"
    ACCEPTANCE_AUTHORITY_GRANTED = "ACCEPTANCE_AUTHORITY_GRANTED"
    CONTEXT_UPDATED = "CONTEXT_UPDATED"
    CONTEXT_REVIEWED = "CONTEXT_REVIEWED"
    SCOPE_RECORDED = "SCOPE_RECORDED"
    SCOPE_APPROVED = "SCOPE_APPROVED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    DOCUMENT_REVISION_RECORDED = "DOCUMENT_REVISION_RECORDED"
    DOCUMENT_LIFECYCLE_CHANGED = "DOCUMENT_LIFECYCLE_CHANGED"
    EVIDENCE_ATTACHED = "EVIDENCE_ATTACHED"
    EVIDENCE_DOWNLOADED = "EVIDENCE_DOWNLOADED"
    EVIDENCE_RETENTION_CHANGED = "EVIDENCE_RETENTION_CHANGED"
    EVIDENCE_PURGED = "EVIDENCE_PURGED"
    SOA_RELEASE_RECORDED = "SOA_RELEASE_RECORDED"
    SOA_RELEASE_APPROVED = "SOA_RELEASE_APPROVED"
    TREATMENT_PLAN_UPDATED = "TREATMENT_PLAN_UPDATED"
    TREATMENT_MILESTONE_UPDATED = "TREATMENT_MILESTONE_UPDATED"
    TREATMENT_PLAN_APPROVED = "TREATMENT_PLAN_APPROVED"
    TREATMENT_PLAN_CLOSED = "TREATMENT_PLAN_CLOSED"
    ISMS_PLAN_UPDATED = "ISMS_PLAN_UPDATED"
    ISMS_PLAN_APPROVED = "ISMS_PLAN_APPROVED"
    ISMS_CHANGE_IMPLEMENTED = "ISMS_CHANGE_IMPLEMENTED"
    ISMS_PLAN_EVALUATED = "ISMS_PLAN_EVALUATED"
    PROOF_BOUND = "PROOF_BOUND"
    TEST_DISPOSITION_RECORDED = "TEST_DISPOSITION_RECORDED"
    REASSESSMENT_RESOLVED = "REASSESSMENT_RESOLVED"
    RESIDUAL_RESCORED = "RESIDUAL_RESCORED"
    SOA_ENTRY_UPDATED = "SOA_ENTRY_UPDATED"
    CONTROL_EFFECTIVENESS_UPDATED = "CONTROL_EFFECTIVENESS_UPDATED"
    CONTROL_TEST_RECORDED = "CONTROL_TEST_RECORDED"
    RISK_EXCEPTION_RECORDED = "RISK_EXCEPTION_RECORDED"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_record", "record_type", "record_ref"),
        Index("ix_audit_events_actor", "actor_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ``created_at`` on the base class is when it happened. It is a wall-clock fact,
    # not a business date, so it does not go through core/clock.py.

    actor_username: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)

    action: Mapped[str] = mapped_column(String(48), nullable=False)

    # RISK, SOA_ENTRY, CONTROL, CONTROL_TEST, RISK_EXCEPTION -- and the business
    # reference within it.
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    record_ref: Mapped[str] = mapped_column(String(32), nullable=False)

    # The changed fields before and after. ``before`` is NULL for a creation.
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict] = mapped_column(JSON, nullable=False)

    # One sentence a reader can act on without opening the JSON:
    # "Residual re-scored from 3 x 5 (15, HIGH) to 2 x 5 (10, MEDIUM)."
    summary: Mapped[str] = mapped_column(Text, nullable=False)
