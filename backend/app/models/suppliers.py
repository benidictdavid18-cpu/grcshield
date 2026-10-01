from datetime import date

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint(
            "criticality IN ('UNASSESSED','LOW','MEDIUM','HIGH','CRITICAL')",
            name="ck_supplier_criticality",
        ),
        CheckConstraint("status IN ('DRAFT','REVIEWED','EXITED')", name="ck_supplier_status"),
        CheckConstraint(
            "length(trim(name))>0 AND length(trim(owner))>0 AND length(trim(service))>0",
            name="ck_supplier_required",
        ),
        CheckConstraint(
            "status != 'REVIEWED' OR (criticality != 'UNASSESSED' AND reviewed_on IS NOT NULL AND review_date > reviewed_on)",
            name="ck_supplier_review",
        ),
        CheckConstraint(
            "dependency_id IS NULL OR dependency_id != id", name="ck_supplier_self_dependency"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_ref: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(240))
    service: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    criticality: Mapped[str] = mapped_column(String(16), default="UNASSESSED")
    information_access: Mapped[str] = mapped_column(Text)
    agreement_terms: Mapped[str] = mapped_column(Text)
    shared_responsibility: Mapped[str] = mapped_column(Text)
    exit_plan: Mapped[str] = mapped_column(Text)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="RESTRICT"))
    dependency_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT")
    )
    agreement_attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_attachments.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    reviewed_on: Mapped[date | None] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(default=1)


class SupplierReview(Base):
    __tablename__ = "supplier_reviews"
    __table_args__ = (
        CheckConstraint(
            "result IN ('ACCEPTABLE','ACTION_REQUIRED','EXIT')", name="ck_supplier_review_result"
        ),
        CheckConstraint(
            "result != 'ACTION_REQUIRED' OR (action_due IS NOT NULL AND length(trim(action_owner))>0 AND length(trim(action))>0)",
            name="ck_supplier_review_action",
        ),
        CheckConstraint(
            "action_due IS NULL OR action_due >= reviewed_on", name="ck_supplier_action_date"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    reviewed_on: Mapped[date] = mapped_column(Date)
    actor: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    action: Mapped[str | None] = mapped_column(Text)
    action_owner: Mapped[str | None] = mapped_column(String(160))
    action_due: Mapped[date | None] = mapped_column(Date)
    completed_on: Mapped[date | None] = mapped_column(Date)
    completion_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT")
    )
    completion_note: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSON)
