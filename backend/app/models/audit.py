"""Control testing workpapers, audit findings and the ISO 27001 clause-level records.

Clause coverage:
    9.2  internal_audit_programme
    9.3  management_reviews
    10.2 nonconformities

Rules and their justification live in ``app.services.control_testing``.
"""

from datetime import date

from sqlalchemy import (
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
from app.models.risk import Control
from app.models.soa import Evidence, RemediationItem
from app.services.control_testing import (
    AuditStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    NonconformityStatus,
    SampleSelectionMethod,
    TestConclusion,
)


class AuditFinding(Base):
    """A deficiency identified by testing, audit, management review or an incident.

    Created as DRAFT when a control test concludes FAIL or PASS_WITH_EXCEPTIONS. Draft
    is the honest starting state: the system observed a fact, but whether it is a
    finding worth raising — and at what severity — is a human judgment.
    """

    __tablename__ = "audit_findings"
    __table_args__ = (Index("ix_audit_findings_status", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"), nullable=False
    )
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status"), nullable=False
    )
    source: Mapped[FindingSource] = mapped_column(
        Enum(FindingSource, name="finding_source"), nullable=False
    )
    identified_date: Mapped[date] = mapped_column(Date, nullable=False)
    identified_by: Mapped[str] = mapped_column(String(120), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    control_id: Mapped[int | None] = mapped_column(
        ForeignKey("controls.id", ondelete="SET NULL"), nullable=True
    )
    control: Mapped[Control | None] = relationship()

    remediation_links: Mapped[list["FindingRemediationLink"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )

    @property
    def linked_remediation(self) -> list[RemediationItem]:
        return sorted(
            (link.remediation for link in self.remediation_links),
            key=lambda item: item.remediation_ref,
        )

    @property
    def is_open(self) -> bool:
        return self.status in (FindingStatus.DRAFT, FindingStatus.OPEN)


class FindingRemediationLink(Base):
    __tablename__ = "finding_remediation_links"
    __table_args__ = (
        UniqueConstraint("finding_id", "remediation_id", name="uq_finding_remediation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("audit_findings.id", ondelete="CASCADE"), nullable=False
    )
    remediation_id: Mapped[int] = mapped_column(
        ForeignKey("remediation_items.id", ondelete="CASCADE"), nullable=False
    )

    finding: Mapped[AuditFinding] = relationship(back_populates="remediation_links")
    remediation: Mapped[RemediationItem] = relationship()


class ControlTestEvidenceLink(Base):
    __tablename__ = "control_test_evidence_links"
    __table_args__ = (
        UniqueConstraint("control_test_id", "evidence_id", name="uq_control_test_evidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    control_test_id: Mapped[int] = mapped_column(
        ForeignKey("control_tests.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )

    control_test: Mapped["ControlTest"] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship()


class ControlTest(Base):
    """A workpaper: what was tested, over what period, how the sample was chosen,
    what was found, and who reviewed it."""

    __tablename__ = "control_tests"
    __table_args__ = (Index("ix_control_tests_control", "control_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    control_id: Mapped[int] = mapped_column(
        ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )

    tester: Mapped[str] = mapped_column(String(120), nullable=False)
    test_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_covered_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_covered_end: Mapped[date] = mapped_column(Date, nullable=False)

    test_objective: Mapped[str] = mapped_column(Text, nullable=False)
    test_procedure: Mapped[str] = mapped_column(Text, nullable=False)

    population_description: Mapped[str] = mapped_column(Text, nullable=False)
    population_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_selection_method: Mapped[SampleSelectionMethod] = mapped_column(
        Enum(SampleSelectionMethod, name="sample_selection_method"), nullable=False
    )
    sampling_rationale: Mapped[str] = mapped_column(Text, nullable=False)

    results_summary: Mapped[str] = mapped_column(Text, nullable=False)
    exceptions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exception_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[TestConclusion] = mapped_column(
        Enum(TestConclusion, name="test_conclusion"), nullable=False
    )

    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    linked_finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_findings.id", ondelete="SET NULL"), nullable=True
    )

    control: Mapped[Control] = relationship()
    linked_finding: Mapped[AuditFinding | None] = relationship()
    evidence_links: Mapped[list[ControlTestEvidenceLink]] = relationship(
        back_populates="control_test", cascade="all, delete-orphan"
    )

    @property
    def linked_evidence(self) -> list[Evidence]:
        return sorted(
            (link.evidence for link in self.evidence_links), key=lambda e: e.evidence_ref
        )

    @property
    def exception_rate(self) -> float:
        return round(self.exceptions_count / self.sample_size, 4) if self.sample_size else 0.0

    @property
    def is_reviewed(self) -> bool:
        return bool(self.reviewed_by) and self.review_date is not None


class InternalAudit(Base):
    """ISO/IEC 27001:2022 Clause 9.2 — internal audit programme."""

    __tablename__ = "internal_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    objectives: Mapped[str] = mapped_column(Text, nullable=False)
    criteria: Mapped[str] = mapped_column(Text, nullable=False)
    auditor: Mapped[str] = mapped_column(String(160), nullable=False)

    # Clause 9.2.2 c) requires auditors not to audit their own work. At forty people
    # that is genuinely hard, so the basis is recorded rather than assumed.
    independence_note: Mapped[str] = mapped_column(Text, nullable=False)

    planned_start: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end: Mapped[date] = mapped_column(Date, nullable=False)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status"), nullable=False
    )
    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class ManagementReview(Base):
    """ISO/IEC 27001:2022 Clause 9.3 — management review.

    Clause 9.3.2 lists the required inputs; ``inputs_considered`` records them so the
    review can be shown to have covered what the standard asks for.
    """

    __tablename__ = "management_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    chair: Mapped[str] = mapped_column(String(120), nullable=False)
    attendees: Mapped[str] = mapped_column(Text, nullable=False)
    inputs_considered: Mapped[str] = mapped_column(Text, nullable=False)
    decisions: Mapped[str] = mapped_column(Text, nullable=False)
    actions: Mapped[str] = mapped_column(Text, nullable=False)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Nonconformity(Base):
    """ISO/IEC 27001:2022 Clause 10.2 — nonconformity and corrective action.

    The correction / corrective action split is the point of this record. A correction
    fixes the instance; corrective action eliminates the cause so it does not recur.
    Clause 10.2 requires both, plus a review of whether the action worked.
    """

    __tablename__ = "nonconformities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nc_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[FindingSource] = mapped_column(
        Enum(FindingSource, name="finding_source"), nullable=False
    )
    identified_date: Mapped[date] = mapped_column(Date, nullable=False)
    identified_by: Mapped[str] = mapped_column(String(120), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)

    immediate_correction: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effectiveness_check_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effectiveness_check_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[NonconformityStatus] = mapped_column(
        Enum(NonconformityStatus, name="nonconformity_status"), nullable=False
    )
    closure_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_findings.id", ondelete="SET NULL"), nullable=True
    )
    finding: Mapped[AuditFinding | None] = relationship()
