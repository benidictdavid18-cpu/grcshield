"""Maintained assurance records supplement, rather than re-sign, historical records."""

from datetime import date

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditProgramme(Base):
    __tablename__ = "audit_programmes"
    __table_args__ = (
        CheckConstraint(
            "review_date >= starts_on AND ends_on >= starts_on", name="ck_programme_dates"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    programme_ref: Mapped[str] = mapped_column(String(32), unique=True)
    owner: Mapped[str] = mapped_column(String(160))
    risk_basis: Mapped[str] = mapped_column(Text)
    coverage: Mapped[str] = mapped_column(Text)
    frequency: Mapped[str] = mapped_column(Text)
    methods: Mapped[str] = mapped_column(Text)
    reporting: Mapped[str] = mapped_column(Text)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    review_date: Mapped[date] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class AssuranceCycle(Base):
    __tablename__ = "assurance_cycles"
    __table_args__ = (
        CheckConstraint(
            "(kind='AUDIT' AND audit_id IS NOT NULL AND review_id IS NULL AND programme_id IS NOT NULL) OR (kind='REVIEW' AND review_id IS NOT NULL AND audit_id IS NULL AND programme_id IS NULL)",
            name="ck_assurance_kind",
        ),
        CheckConstraint(
            "status IN ('DRAFT','IN_PROGRESS','COMPLETED')", name="ck_assurance_status"
        ),
        CheckConstraint(
            "status != 'COMPLETED' OR (completed_on IS NOT NULL AND completed_by IS NOT NULL AND evidence_id IS NOT NULL AND completion_snapshot IS NOT NULL)",
            name="ck_assurance_completion",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_ref: Mapped[str] = mapped_column(String(32), unique=True)
    kind: Mapped[str] = mapped_column(String(16))
    audit_id: Mapped[int | None] = mapped_column(
        ForeignKey("internal_audits.id", ondelete="RESTRICT"), unique=True
    )
    review_id: Mapped[int | None] = mapped_column(
        ForeignKey("management_reviews.id", ondelete="RESTRICT"), unique=True
    )
    programme_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_programmes.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    completed_on: Mapped[date | None] = mapped_column(Date)
    completed_by: Mapped[str | None] = mapped_column(String(64))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    completion_snapshot: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))


class AssuranceInput(Base):
    __tablename__ = "assurance_inputs"
    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assurance_cycles.id", ondelete="RESTRICT"))
    category: Mapped[str] = mapped_column(String(48))
    consideration: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    no_evidence_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("cycle_id", "category", name="uq_assurance_input"),
        CheckConstraint(
            "evidence_id IS NOT NULL OR length(trim(coalesce(no_evidence_reason,'')))>0",
            name="ck_assurance_input_basis",
        ),
    )


class AssuranceAction(Base):
    __tablename__ = "assurance_actions"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','COMPLETED')", name="ck_assurance_action_status"),
        CheckConstraint(
            "status != 'COMPLETED' OR (evidence_id IS NOT NULL AND completed_on IS NOT NULL AND completed_by IS NOT NULL AND length(trim(coalesce(completion_note,'')))>0)",
            name="ck_assurance_action_completion",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    action_ref: Mapped[str] = mapped_column(String(32), unique=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assurance_cycles.id", ondelete="RESTRICT"))
    description: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    due_date: Mapped[date] = mapped_column(Date)
    finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_findings.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    completed_on: Mapped[date | None] = mapped_column(Date)
    completed_by: Mapped[str | None] = mapped_column(String(64))
    completion_note: Mapped[str | None] = mapped_column(Text)


class CorrectiveVerification(Base):
    __tablename__ = "corrective_verifications"
    __table_args__ = (
        CheckConstraint("result IN ('EFFECTIVE','INEFFECTIVE')", name="ck_corrective_result"),
        CheckConstraint(
            "length(trim(note))>0 AND length(trim(actor))>0", name="ck_corrective_note"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    nonconformity_id: Mapped[int] = mapped_column(
        ForeignKey("nonconformities.id", ondelete="RESTRICT")
    )
    checked_on: Mapped[date] = mapped_column(Date)
    result: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    actor: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
