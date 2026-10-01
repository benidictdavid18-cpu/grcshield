from datetime import date

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegisterRevision(Base):
    __tablename__ = "register_revisions"
    __table_args__ = (
        UniqueConstraint("kind", "record_ref", "revision", name="uq_register_revision"),
        CheckConstraint("kind IN ('ASSET','ROPA','DPIA','BIA')", name="ck_register_kind"),
        CheckConstraint("status IN ('DRAFT','REVIEWED')", name="ck_register_status"),
        CheckConstraint(
            "status != 'REVIEWED' OR (reviewed_by IS NOT NULL AND reviewed_on IS NOT NULL AND evidence_id IS NOT NULL)",
            name="ck_register_review",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    record_ref: Mapped[str] = mapped_column(String(24))
    revision: Mapped[int] = mapped_column()
    owner: Mapped[str] = mapped_column(String(160))
    review_date: Mapped[date] = mapped_column(Date)
    change_note: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    content: Mapped[dict] = mapped_column(JSON)
    previous: Mapped[dict | None] = mapped_column(JSON)
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    reviewed_on: Mapped[date | None] = mapped_column(Date)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))


class RiskAsset(Base):
    __tablename__ = "risk_assets"
    __table_args__ = (UniqueConstraint("risk_id", "asset_id", name="uq_risk_asset"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="RESTRICT"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT"))


class OperationalReviewTask(Base):
    __tablename__ = "operational_review_tasks"
    __table_args__ = (
        UniqueConstraint("revision_id", "risk_id", name="uq_operational_review"),
        CheckConstraint("status IN ('OPEN','RESOLVED')", name="ck_operational_task_status"),
        CheckConstraint(
            "status != 'RESOLVED' OR (evidence_id IS NOT NULL AND resolved_by IS NOT NULL AND length(trim(coalesce(resolution,'')))>0)",
            name="ck_operational_task_resolution",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("register_revisions.id", ondelete="RESTRICT")
    )
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="RESTRICT"))
    owner: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    resolved_by: Mapped[str | None] = mapped_column(String(64))


class OperationalEvidence(Base):
    __tablename__ = "operational_evidence"
    __table_args__ = (
        CheckConstraint(
            "period_end >= period_start AND review_date >= period_end",
            name="ck_operational_evidence_dates",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id", ondelete="RESTRICT"))
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    source_system: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    review_date: Mapped[date] = mapped_column(Date)
    coverage_note: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(64))


class ContinuityExercise(Base):
    __tablename__ = "continuity_exercises"
    __table_args__ = (
        CheckConstraint(
            "recovery_hours >= 0 AND data_loss_hours >= 0", name="ck_exercise_measurements"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_ref: Mapped[str] = mapped_column(String(32), unique=True)
    bia_id: Mapped[int] = mapped_column(
        ForeignKey("business_impact_analyses.id", ondelete="RESTRICT")
    )
    performed_on: Mapped[date] = mapped_column(Date)
    recovery_hours: Mapped[float] = mapped_column(Float)
    data_loss_hours: Mapped[float] = mapped_column(Float)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    actor: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text)
    follow_up: Mapped[str] = mapped_column(Text)
    target_snapshot: Mapped[dict] = mapped_column(JSON)
