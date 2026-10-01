from datetime import date

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Obligation(Base):
    __tablename__ = "obligations"
    __table_args__ = (
        CheckConstraint("kind IN ('LEGAL','REGULATORY','CONTRACTUAL')", name="ck_obligation_kind"),
        CheckConstraint(
            "applicability IN ('UNASSESSED','APPLICABLE','NOT_APPLICABLE')",
            name="ck_obligation_applicability",
        ),
        CheckConstraint(
            "length(trim(source))>0 AND length(trim(source_version))>0 AND length(trim(owner))>0",
            name="ck_obligation_source",
        ),
        CheckConstraint(
            "applicability='UNASSESSED' OR (approved_by IS NOT NULL AND approved_on IS NOT NULL AND length(trim(coalesce(rationale,'')))>0)",
            name="ck_obligation_approval",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    obligation_ref: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    kind: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(Text)
    source_version: Mapped[str] = mapped_column(String(160))
    jurisdiction: Mapped[str] = mapped_column(String(160))
    requirement: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    review_date: Mapped[date] = mapped_column(Date)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="RESTRICT"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    applicability: Mapped[str] = mapped_column(String(16), default="UNASSESSED")
    rationale: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_on: Mapped[date | None] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(default=1)


class ObligationDecision(Base):
    __tablename__ = "obligation_decisions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('APPLICABILITY','EVALUATION')", name="ck_obligation_decision_kind"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    obligation_id: Mapped[int] = mapped_column(ForeignKey("obligations.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16))
    decided_on: Mapped[date] = mapped_column(Date)
    actor: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    remediation_id: Mapped[int | None] = mapped_column(
        ForeignKey("remediation_items.id", ondelete="RESTRICT")
    )
    snapshot: Mapped[dict] = mapped_column(JSON)
