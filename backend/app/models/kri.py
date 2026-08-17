"""Key risk indicators.

A KRI is a definition plus a series of measurements. Splitting them matters: the
definition says what is being counted and what good looks like, and the measurement
series is the record of what was actually observed. A dashboard number with no
definition behind it is a chart, and a definition with no history is an opinion.

Thresholds are stored on the definition, with a direction, because "green above 95" and
"green below 14" are both normal and a single comparison operator cannot serve both.
"""

import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KriDirection(str, enum.Enum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"


class KriUnit(str, enum.Enum):
    PERCENT = "PERCENT"
    COUNT = "COUNT"
    DAYS = "DAYS"


class KriBand(str, enum.Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    NO_DATA = "NO_DATA"


class MeasurementFrequency(str, enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class KriDefinition(Base):
    __tablename__ = "kri_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kri_ref: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # What is counted, over what population, and any substitution made. This is the
    # field that stops two people computing the same "percentage" differently.
    formula_description: Mapped[str] = mapped_column(Text, nullable=False)
    data_source: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    unit: Mapped[KriUnit] = mapped_column(Enum(KriUnit, name="kri_unit"), nullable=False)
    direction: Mapped[KriDirection] = mapped_column(
        Enum(KriDirection, name="kri_direction"), nullable=False
    )
    green_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    amber_threshold: Mapped[float] = mapped_column(Float, nullable=False)

    owner_role: Mapped[str] = mapped_column(String(120), nullable=False)
    measurement_frequency: Mapped[MeasurementFrequency] = mapped_column(
        Enum(MeasurementFrequency, name="measurement_frequency"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    measurements: Mapped[list["KriMeasurement"]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="KriMeasurement.period_end",
    )

    def band_for(self, value: float | None) -> KriBand:
        """Classify a value against this KRI's thresholds.

        ``None`` is NO_DATA rather than zero. A metric with nothing to measure is not
        performing perfectly; it is not being measured, and those look identical on a
        dashboard unless the difference is kept.
        """
        if value is None:
            return KriBand.NO_DATA
        if self.direction == KriDirection.HIGHER_IS_BETTER:
            if value >= self.green_threshold:
                return KriBand.GREEN
            return KriBand.AMBER if value >= self.amber_threshold else KriBand.RED
        if value <= self.green_threshold:
            return KriBand.GREEN
        return KriBand.AMBER if value <= self.amber_threshold else KriBand.RED


class KriMeasurement(Base):
    """One observation of one KRI at one period end."""

    __tablename__ = "kri_measurements"
    __table_args__ = (UniqueConstraint("kri_id", "period_end", name="uq_kri_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kri_id: Mapped[int] = mapped_column(
        ForeignKey("kri_definitions.id", ondelete="CASCADE"), nullable=False
    )
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    definition: Mapped[KriDefinition] = relationship(back_populates="measurements")
