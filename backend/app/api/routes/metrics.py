"""KRI dashboard and the executive view."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.kri import KriBand, KriDefinition, KriDirection, KriUnit, MeasurementFrequency
from app.services import executive as executive_service
from app.services.kri_engine import compute

router = APIRouter(tags=["metrics"])

TREND_POINTS = 6


class TrendPoint(BaseModel):
    period_end: date
    value: float | None
    band: KriBand
    is_current: bool


class KriOut(BaseModel):
    kri_ref: str
    name: str
    formula_description: str
    data_source: str
    rationale: str
    unit: KriUnit
    direction: KriDirection
    green_threshold: float
    amber_threshold: float
    owner_role: str
    measurement_frequency: MeasurementFrequency
    current_value: float | None
    current_band: KriBand
    current_detail: str
    trend: list[TrendPoint]
    movement: str


def _movement(trend: list[TrendPoint], direction: KriDirection) -> str:
    """Whether the indicator is getting better, worse, or holding.

    Compares the current value with the earliest point that has one. Direction matters:
    a falling mean-time-to-remediate is an improvement, a falling implementation
    percentage is not.
    """
    points = [p for p in trend if p.value is not None]
    if len(points) < 2:
        return "NO_TREND"
    first, last = points[0].value, points[-1].value
    if first == last:
        return "FLAT"
    rising = last > first
    better = rising if direction == KriDirection.HIGHER_IS_BETTER else not rising
    return "IMPROVING" if better else "DETERIORATING"


@router.get("/kris", response_model=list[KriOut])
def list_kris(db: Session = Depends(get_db)) -> list[KriOut]:
    """The KRI set, with recorded history and a live current value.

    Historical points come from ``kri_measurements`` — what was observed at each period
    end. The current point is computed from the registers on this request, so the
    dashboard cannot drift away from the data behind it.
    """
    today = date.today()
    definitions = db.scalars(
        select(KriDefinition)
        .options(selectinload(KriDefinition.measurements))
        .order_by(KriDefinition.sort_order)
    ).all()

    out: list[KriOut] = []
    for definition in definitions:
        computed = compute(db, definition, today)
        history = [
            TrendPoint(
                period_end=m.period_end,
                value=m.value,
                band=definition.band_for(m.value),
                is_current=False,
            )
            for m in sorted(definition.measurements, key=lambda m: m.period_end)
            if m.period_end < today
        ][-(TREND_POINTS - 1):]

        trend = history + [
            TrendPoint(
                period_end=today,
                value=computed.value,
                band=definition.band_for(computed.value),
                is_current=True,
            )
        ]

        out.append(
            KriOut(
                kri_ref=definition.kri_ref,
                name=definition.name,
                formula_description=definition.formula_description,
                data_source=definition.data_source,
                rationale=definition.rationale,
                unit=definition.unit,
                direction=definition.direction,
                green_threshold=definition.green_threshold,
                amber_threshold=definition.amber_threshold,
                owner_role=definition.owner_role,
                measurement_frequency=definition.measurement_frequency,
                current_value=computed.value,
                current_band=definition.band_for(computed.value),
                current_detail=computed.detail,
                trend=trend,
                movement=_movement(trend, definition.direction),
            )
        )
    return out


@router.get("/kris/{kri_ref}", response_model=KriOut)
def get_kri(kri_ref: str, db: Session = Depends(get_db)) -> KriOut:
    match = [k for k in list_kris(db) if k.kri_ref == kri_ref.upper()]
    if not match:
        raise HTTPException(status_code=404, detail=f"Unknown indicator '{kri_ref}'")
    return match[0]


class TopRiskOut(BaseModel):
    # The service returns dataclasses; from_attributes lets them validate into the
    # response model rather than failing serialisation at the boundary.
    model_config = ConfigDict(from_attributes=True)

    risk_ref: str
    plain_title: str
    what_could_happen: str
    who_owns_it: str
    beyond_agreed_limit: bool


class GapOut(BaseModel):
    what_is_missing: str
    detail: str
    risks_depending_on_it: int
    owner: str


class PriorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    headline: str
    why: str
    owner: str
    by_when: str


class ThirdPartyOut(BaseModel):
    risks_tracked: int
    beyond_agreed_limit: int
    summary: str


class ExecutiveSummaryOut(BaseModel):
    as_of: date
    posture_statement: str
    posture_key: str
    risks_total: int
    risks_beyond_agreed_limit: int
    risks_carried_without_a_decision: int
    safeguards_required: int
    safeguards_in_place: int
    safeguards_percent: float
    top_risks: list[TopRiskOut]
    top_gaps: list[GapOut]
    open_findings_by_severity: dict[str, int]
    open_findings_total: int
    remediation_open: int
    remediation_overdue: int
    third_party: ThirdPartyOut
    categories: dict[str, int]
    priorities: list[PriorityOut]


@router.get("/executive-summary", response_model=ExecutiveSummaryOut)
def executive_summary(db: Session = Depends(get_db)) -> ExecutiveSummaryOut:
    """The board view: same numbers, no jargon, no control identifiers in the prose."""
    return ExecutiveSummaryOut(**executive_service.build(db, date.today()))
