"""Treatment commitments, milestones and evidence-backed completion."""
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TreatmentPlan(Base):
    __tablename__="treatment_plans"
    __table_args__=(
        UniqueConstraint("id","review_deadline",name="uq_plan_deadline"),
        CheckConstraint("status IN ('DRAFT','APPROVED','COMPLETED','CANCELLED')",name="ck_plan_status"),
        CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(resources))>0 AND length(trim(rationale))>0",name="ck_plan_required"),
        CheckConstraint("status NOT IN ('APPROVED','COMPLETED') OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND approved_snapshot IS NOT NULL AND approval_note IS NOT NULL AND length(trim(approval_note))>0)",name="ck_plan_approval"),
        CheckConstraint("status != 'COMPLETED' OR (verification_evidence_id IS NOT NULL AND verification_note IS NOT NULL AND length(trim(verification_note))>0 AND closed_by IS NOT NULL)",name="ck_plan_completion"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plan_ref: Mapped[str]=mapped_column(String(32),unique=True)
    risk_id: Mapped[int]=mapped_column(ForeignKey("risks.id",ondelete="RESTRICT"))
    title: Mapped[str]=mapped_column(String(240))
    owner: Mapped[str]=mapped_column(String(160))
    resources: Mapped[str]=mapped_column(Text)
    rationale: Mapped[str]=mapped_column(Text)
    review_deadline: Mapped[date]=mapped_column(Date)
    status: Mapped[str]=mapped_column(String(16),default="DRAFT")
    revision: Mapped[int]=mapped_column(Integer,default=1)
    approved_by: Mapped[str | None]=mapped_column(String(64))
    approved_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    approved_snapshot: Mapped[dict | None]=mapped_column(JSON(none_as_null=True))
    approval_note: Mapped[str | None]=mapped_column(Text)
    verification_evidence_id: Mapped[int | None]=mapped_column(ForeignKey("evidence.id",ondelete="RESTRICT"))
    verification_note: Mapped[str | None]=mapped_column(Text)
    closed_by: Mapped[str | None]=mapped_column(String(64))

class TreatmentControl(Base):
    __tablename__="treatment_control_links"
    __table_args__=(UniqueConstraint("plan_id","control_id",name="uq_treatment_control"),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plan_id: Mapped[int]=mapped_column(ForeignKey("treatment_plans.id",ondelete="RESTRICT"))
    control_id: Mapped[int]=mapped_column(ForeignKey("controls.id",ondelete="RESTRICT"))

class TreatmentMilestone(Base):
    __tablename__="treatment_milestones"
    __table_args__=(
        UniqueConstraint("plan_id","milestone_ref",name="uq_plan_milestone"),
        UniqueConstraint("id","plan_id",name="uq_milestone_plan"),
        ForeignKeyConstraint(["plan_id","review_deadline"],["treatment_plans.id","treatment_plans.review_deadline"],name="fk_milestone_deadline",onupdate="CASCADE",ondelete="RESTRICT"),
        ForeignKeyConstraint(["dependency_id","plan_id"],["treatment_milestones.id","treatment_milestones.plan_id"],name="fk_milestone_dependency",ondelete="RESTRICT"),
        CheckConstraint("due_date <= review_deadline",name="ck_milestone_review_deadline"),
        CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0",name="ck_milestone_required"),
        CheckConstraint("status IN ('OPEN','IN_PROGRESS','COMPLETED')",name="ck_milestone_status"),
        CheckConstraint("dependency_id IS NULL OR dependency_id != id",name="ck_milestone_not_self"),
        CheckConstraint("status != 'COMPLETED' OR (evidence_id IS NOT NULL AND completed_on IS NOT NULL AND completed_by IS NOT NULL AND completion_note IS NOT NULL AND length(trim(completion_note))>0)",name="ck_milestone_completion"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plan_id: Mapped[int]=mapped_column(Integer)
    review_deadline: Mapped[date]=mapped_column(Date)
    milestone_ref: Mapped[str]=mapped_column(String(32))
    title: Mapped[str]=mapped_column(String(240))
    owner: Mapped[str]=mapped_column(String(160))
    due_date: Mapped[date]=mapped_column(Date)
    dependency_id: Mapped[int | None]=mapped_column(Integer)
    remediation_id: Mapped[int | None]=mapped_column(ForeignKey("remediation_items.id",ondelete="RESTRICT"))
    status: Mapped[str]=mapped_column(String(16),default="OPEN")
    evidence_id: Mapped[int | None]=mapped_column(ForeignKey("evidence.id",ondelete="RESTRICT"))
    completion_note: Mapped[str | None]=mapped_column(Text)
    completed_on: Mapped[date | None]=mapped_column(Date)
    completed_by: Mapped[str | None]=mapped_column(String(64))
