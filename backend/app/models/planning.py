"""Owned objectives and deliberate changes to the management system."""
from datetime import date,datetime
from sqlalchemy import CheckConstraint,Date,DateTime,Float,ForeignKey,Integer,JSON,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base

class ISMSPlan(Base):
    __tablename__="isms_plans"
    __table_args__=(
        CheckConstraint("kind IN ('OBJECTIVE','CHANGE')",name="ck_isms_plan_kind"),
        CheckConstraint("status IN ('DRAFT','APPROVED','IMPLEMENTED','EVALUATED','CANCELLED')",name="ck_isms_plan_status"),
        CheckConstraint("length(trim(title))>0 AND length(trim(owner))>0 AND length(trim(resources))>0 AND length(trim(rationale))>0",name="ck_isms_plan_required"),
        CheckConstraint("direction IS NULL OR direction IN ('HIGHER_IS_BETTER','LOWER_IS_BETTER')",name="ck_isms_plan_direction"),
        CheckConstraint("status IN ('DRAFT','CANCELLED') OR (due_date IS NOT NULL AND approved_by IS NOT NULL AND approved_at IS NOT NULL AND approval_note IS NOT NULL AND approved_snapshot IS NOT NULL AND ((kind='OBJECTIVE' AND measure_definition IS NOT NULL AND target_value IS NOT NULL AND direction IS NOT NULL) OR (kind='CHANGE' AND impact_assessment IS NOT NULL AND rollback_plan IS NOT NULL)))",name="ck_isms_plan_approval"),
        CheckConstraint("status != 'IMPLEMENTED' OR (kind='CHANGE' AND implementation_date IS NOT NULL AND implementation_evidence_id IS NOT NULL AND implementation_note IS NOT NULL)",name="ck_isms_change_implementation"),
    )
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plan_ref: Mapped[str]=mapped_column(String(32),unique=True)
    kind: Mapped[str]=mapped_column(String(16))
    title: Mapped[str]=mapped_column(String(240))
    owner: Mapped[str]=mapped_column(String(160))
    resources: Mapped[str]=mapped_column(Text)
    rationale: Mapped[str]=mapped_column(Text)
    context_id: Mapped[int]=mapped_column(ForeignKey("isms_context.id",ondelete="RESTRICT"))
    risk_id: Mapped[int | None]=mapped_column(ForeignKey("risks.id",ondelete="RESTRICT"))
    kri_id: Mapped[int | None]=mapped_column(ForeignKey("kri_definitions.id",ondelete="RESTRICT"))
    due_date: Mapped[date | None]=mapped_column(Date)
    measure_definition: Mapped[str | None]=mapped_column(Text)
    target_value: Mapped[float | None]=mapped_column(Float)
    direction: Mapped[str | None]=mapped_column(String(24))
    impact_assessment: Mapped[str | None]=mapped_column(Text)
    rollback_plan: Mapped[str | None]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(16),default="DRAFT")
    revision: Mapped[int]=mapped_column(Integer,default=1)
    approved_by: Mapped[str | None]=mapped_column(String(64))
    approved_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    approved_snapshot: Mapped[dict | None]=mapped_column(JSON(none_as_null=True))
    approval_note: Mapped[str | None]=mapped_column(Text)
    implementation_date: Mapped[date | None]=mapped_column(Date)
    implementation_evidence_id: Mapped[int | None]=mapped_column(ForeignKey("evidence.id",ondelete="RESTRICT"))
    implementation_note: Mapped[str | None]=mapped_column(Text)
    cancellation_note: Mapped[str | None]=mapped_column(Text)

class PlanEvaluation(Base):
    __tablename__="isms_plan_evaluations"
    __table_args__=(CheckConstraint("length(trim(evaluation_note))>0 AND length(trim(actor))>0",name="ck_plan_evaluation_note"),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plan_id: Mapped[int]=mapped_column(ForeignKey("isms_plans.id",ondelete="RESTRICT"))
    observed_on: Mapped[date]=mapped_column(Date)
    observed_value: Mapped[float | None]=mapped_column(Float)
    evaluation_note: Mapped[str]=mapped_column(Text)
    evidence_id: Mapped[int]=mapped_column(ForeignKey("evidence.id",ondelete="RESTRICT"))
    actor: Mapped[str]=mapped_column(String(64))
