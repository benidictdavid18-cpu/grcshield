"""Statement of Applicability, evidence and remediation.

The SoA is required by ISO/IEC 27001:2022 Clause 6.1.3 d). It is the document a
certification auditor opens first, because it is where the organisation commits, in
writing, to which Annex A controls apply and why.

Three tables arrive together because the SoA is only meaningful when its claims are
traceable: an applicable control needs evidence that it operates, and a control that
is applicable but not implemented needs a remediation item with an owner and a date.
An SoA without those links is a spreadsheet of assertions.
"""

import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.framework import FrameworkControl
from app.models.risk import Control, Risk


class ImplementationStatus(str, enum.Enum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    PARTIALLY_IMPLEMENTED = "PARTIALLY_IMPLEMENTED"
    IMPLEMENTED = "IMPLEMENTED"


class EvidenceType(str, enum.Enum):
    POLICY = "POLICY"
    CONFIG_EXPORT = "CONFIG_EXPORT"
    REPORT = "REPORT"
    LOG_EXTRACT = "LOG_EXTRACT"
    SCREENSHOT = "SCREENSHOT"
    ATTESTATION = "ATTESTATION"
    CERTIFICATE = "CERTIFICATE"
    TICKET = "TICKET"


class RemediationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RemediationPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RemediationSource(str, enum.Enum):
    SOA_GAP = "SOA_GAP"
    CONTROL_TEST = "CONTROL_TEST"
    AUDIT_FINDING = "AUDIT_FINDING"
    RISK_TREATMENT = "RISK_TREATMENT"


class Evidence(Base):
    """An artifact that demonstrates a control operates.

    Evidence carries a validity window rather than just a collection date. A screenshot
    of an access review from eighteen months ago is not evidence that access reviews
    happen; it is evidence that one happened once. Expiry is what makes the difference
    visible, and it drives the evidence-freshness KRI.
    """

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, name="evidence_type"), nullable=False
    )
    source_system: Mapped[str] = mapped_column(String(120), nullable=False)
    collected_by: Mapped[str] = mapped_column(String(120), nullable=False)
    collected_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    # No file upload in this phase. The reference records where the artifact lives so
    # the chain is honest about what exists rather than implying a document store.
    file_reference: Mapped[str | None] = mapped_column(String(300), nullable=True)

    control_id: Mapped[int | None] = mapped_column(
        ForeignKey("controls.id", ondelete="SET NULL"), nullable=True
    )
    control: Mapped[Control | None] = relationship()

    def is_expired(self, as_of: date) -> bool:
        return self.valid_until < as_of


class RemediationItem(Base):
    """Planned work to close a gap.

    ``owner`` and ``due_date`` are NOT NULL by design. A remediation item without
    someone accountable and a date is a wish, and the SoA validation rule that demands
    one would be satisfiable by an empty promise if these were optional.
    """

    __tablename__ = "remediation_items"
    __table_args__ = (Index("ix_remediation_status", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    remediation_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    # When the work was raised. Without it, "mean time to remediate" has no start point
    # and the metric degrades into "how overdue is it".
    raised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[RemediationStatus] = mapped_column(
        Enum(RemediationStatus, name="remediation_status"), nullable=False
    )
    priority: Mapped[RemediationPriority] = mapped_column(
        Enum(RemediationPriority, name="remediation_priority"), nullable=False
    )
    source: Mapped[RemediationSource] = mapped_column(
        Enum(RemediationSource, name="remediation_source"), nullable=False
    )
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    @property
    def is_open(self) -> bool:
        return self.status not in (RemediationStatus.COMPLETED, RemediationStatus.CANCELLED)

    def is_overdue(self, as_of: date) -> bool:
        return self.is_open and self.due_date < as_of


class SoAControlLink(Base):
    __tablename__ = "soa_control_links"
    __table_args__ = (UniqueConstraint("soa_entry_id", "control_id", name="uq_soa_control"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    soa_entry_id: Mapped[int] = mapped_column(
        ForeignKey("soa_entries.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )

    soa_entry: Mapped["SoAEntry"] = relationship(back_populates="control_links")
    control: Mapped[Control] = relationship()


class SoARiskLink(Base):
    __tablename__ = "soa_risk_links"
    __table_args__ = (UniqueConstraint("soa_entry_id", "risk_id", name="uq_soa_risk"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    soa_entry_id: Mapped[int] = mapped_column(
        ForeignKey("soa_entries.id", ondelete="CASCADE"), nullable=False
    )
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)

    soa_entry: Mapped["SoAEntry"] = relationship(back_populates="risk_links")
    risk: Mapped[Risk] = relationship()


class SoAEvidenceLink(Base):
    __tablename__ = "soa_evidence_links"
    __table_args__ = (UniqueConstraint("soa_entry_id", "evidence_id", name="uq_soa_evidence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    soa_entry_id: Mapped[int] = mapped_column(
        ForeignKey("soa_entries.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )

    soa_entry: Mapped["SoAEntry"] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship()


class SoARemediationLink(Base):
    __tablename__ = "soa_remediation_links"
    __table_args__ = (
        UniqueConstraint("soa_entry_id", "remediation_id", name="uq_soa_remediation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    soa_entry_id: Mapped[int] = mapped_column(
        ForeignKey("soa_entries.id", ondelete="CASCADE"), nullable=False
    )
    remediation_id: Mapped[int] = mapped_column(
        ForeignKey("remediation_items.id", ondelete="CASCADE"), nullable=False
    )

    soa_entry: Mapped["SoAEntry"] = relationship(back_populates="remediation_links")
    remediation: Mapped[RemediationItem] = relationship()


class SoAEntry(Base):
    """One row per Annex A control. Ninety-three rows, always.

    ``control_ref``, ``control_title`` and ``theme`` are stored here as well as being
    reachable through ``framework_control``. That denormalisation is deliberate: the
    SoA is a versioned, approved document, and a historic version must still read
    correctly if the underlying catalogue is ever revised. The seed loader asserts the
    snapshot agrees with the catalogue at load time so the two cannot drift silently.
    """

    __tablename__ = "soa_entries"
    __table_args__ = (Index("ix_soa_entries_theme", "theme"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    framework_control_id: Mapped[int] = mapped_column(
        ForeignKey("framework_controls.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    control_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    control_title: Mapped[str] = mapped_column(String(300), nullable=False)
    theme: Mapped[str] = mapped_column(String(16), nullable=False)

    applicable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    justification_inclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification_exclusion: Mapped[str | None] = mapped_column(Text, nullable=True)

    implementation_status: Mapped[ImplementationStatus] = mapped_column(
        Enum(ImplementationStatus, name="implementation_status"), nullable=False
    )
    implementation_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")

    framework_control: Mapped[FrameworkControl] = relationship()
    control_links: Mapped[list[SoAControlLink]] = relationship(
        back_populates="soa_entry", cascade="all, delete-orphan"
    )
    risk_links: Mapped[list[SoARiskLink]] = relationship(
        back_populates="soa_entry", cascade="all, delete-orphan"
    )
    evidence_links: Mapped[list[SoAEvidenceLink]] = relationship(
        back_populates="soa_entry", cascade="all, delete-orphan"
    )
    remediation_links: Mapped[list[SoARemediationLink]] = relationship(
        back_populates="soa_entry", cascade="all, delete-orphan"
    )

    # --- Derived ----------------------------------------------------------
    @property
    def is_gap(self) -> bool:
        """Applicable but not fully implemented. This is what 'gap' means here."""
        return self.applicable and self.implementation_status != ImplementationStatus.IMPLEMENTED

    @property
    def linked_controls(self) -> list[Control]:
        return sorted((link.control for link in self.control_links), key=lambda c: c.control_id)

    @property
    def linked_risks(self) -> list[Risk]:
        return sorted((link.risk for link in self.risk_links), key=lambda r: r.risk_ref)

    @property
    def linked_evidence(self) -> list[Evidence]:
        return sorted((link.evidence for link in self.evidence_links), key=lambda e: e.evidence_ref)

    @property
    def linked_remediation(self) -> list[RemediationItem]:
        return sorted(
            (link.remediation for link in self.remediation_links),
            key=lambda r: r.remediation_ref,
        )

    @property
    def actionable_remediation(self) -> list[RemediationItem]:
        """Remediation that still represents a plan.

        A cancelled item is not a plan, so it cannot satisfy the rule that a gap must
        carry remediation.
        """
        return [
            item
            for item in self.linked_remediation
            if item.status != RemediationStatus.CANCELLED
        ]
