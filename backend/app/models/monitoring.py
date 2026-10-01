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


class MeasurementPlan(Base):
    __tablename__ = "measurement_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    kri_id: Mapped[int] = mapped_column(
        ForeignKey("kri_definitions.id", ondelete="RESTRICT"), unique=True
    )
    method: Mapped[str] = mapped_column(Text)
    population: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    collection_owner: Mapped[str] = mapped_column(String(160))
    evaluation_owner: Mapped[str] = mapped_column(String(160))
    frequency: Mapped[str] = mapped_column(String(80))
    next_collection: Mapped[date] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(default=1)


class MonitoringObservation(Base):
    __tablename__ = "monitoring_observations"
    __table_args__ = (
        UniqueConstraint("plan_id", "period_end", name="uq_monitoring_period"),
        CheckConstraint("period_end >= period_start", name="ck_monitoring_period"),
        CheckConstraint("band IN ('GREEN','AMBER','RED','NO_DATA')", name="ck_monitoring_band"),
        CheckConstraint(
            "evaluated_on IS NULL OR (evaluated_by IS NOT NULL AND length(trim(coalesce(evaluation,'')))>0)",
            name="ck_monitoring_evaluation",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("measurement_plans.id", ondelete="RESTRICT"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    value: Mapped[float | None] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(16))
    source_query: Mapped[str] = mapped_column(Text)
    population: Mapped[str] = mapped_column(Text)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    actor: Mapped[str] = mapped_column(String(64))
    definition_snapshot: Mapped[dict] = mapped_column(JSON)
    evaluated_on: Mapped[date | None] = mapped_column(Date)
    evaluated_by: Mapped[str | None] = mapped_column(String(64))
    evaluation: Mapped[str | None] = mapped_column(Text)
    remediation_id: Mapped[int | None] = mapped_column(
        ForeignKey("remediation_items.id", ondelete="RESTRICT")
    )


class RiskAssessmentSnapshot(Base):
    __tablename__ = "risk_assessment_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="RESTRICT"))
    assessed_on: Mapped[date] = mapped_column(Date)
    actor: Mapped[str] = mapped_column(String(64))
    basis: Mapped[str] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSON)
