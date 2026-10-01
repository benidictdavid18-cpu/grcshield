from datetime import date

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompetenceRequirement(Base):
    __tablename__ = "competence_requirements"
    __table_args__ = (
        CheckConstraint(
            "length(trim(role))>0 AND length(trim(requirement))>0 AND length(trim(owner))>0",
            name="ck_competence_required",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_ref: Mapped[str] = mapped_column(String(32), unique=True)
    role: Mapped[str] = mapped_column(String(160))
    requirement: Mapped[str] = mapped_column(Text)
    evaluation_method: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    review_date: Mapped[date] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(default=1)


class CompetenceEvaluation(Base):
    __tablename__ = "competence_evaluations"
    __table_args__ = (
        CheckConstraint(
            "result IN ('DEVELOPMENT_REQUIRED','COMPETENT')", name="ck_competence_result"
        ),
        CheckConstraint("review_date > evaluated_on", name="ck_competence_dates"),
        CheckConstraint(
            "result != 'DEVELOPMENT_REQUIRED' OR (action_due IS NOT NULL AND length(trim(coalesce(development_action,'')))>0)",
            name="ck_competence_action",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("competence_requirements.id", ondelete="RESTRICT")
    )
    subject_ref: Mapped[str] = mapped_column(String(64))
    evaluated_on: Mapped[date] = mapped_column(Date)
    review_date: Mapped[date] = mapped_column(Date)
    actor: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(24))
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    demonstrated_outcome: Mapped[str] = mapped_column(Text)
    development_action: Mapped[str | None] = mapped_column(Text)
    action_due: Mapped[date | None] = mapped_column(Date)
    requirement_snapshot: Mapped[dict] = mapped_column(JSON)


class CommunicationPlan(Base):
    __tablename__ = "communication_plans"
    __table_args__ = (
        CheckConstraint(
            "length(trim(audience))>0 AND length(trim(owner))>0 AND length(trim(method))>0",
            name="ck_communication_required",
        ),
        CheckConstraint("status IN ('PLANNED','DELIVERED')", name="ck_communication_status"),
        CheckConstraint(
            "status != 'DELIVERED' OR (delivered_on IS NOT NULL AND evidence_id IS NOT NULL AND delivered_by IS NOT NULL)",
            name="ck_communication_delivery",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    communication_ref: Mapped[str] = mapped_column(String(32), unique=True)
    topic: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    method: Mapped[str] = mapped_column(Text)
    planned_on: Mapped[date] = mapped_column(Date)
    document_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_revisions.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="PLANNED")
    delivered_on: Mapped[date | None] = mapped_column(Date)
    delivered_by: Mapped[str | None] = mapped_column(String(64))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    outcome: Mapped[str | None] = mapped_column(Text)
