from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.context import commit
from app.api.routes.provenance import invoke, require
from app.db.session import get_db
from app.models.kri import KriDefinition
from app.models.monitoring import MeasurementPlan, MonitoringObservation, RiskAssessmentSnapshot
from app.models.risk import Risk
from app.models.user import User
from app.schemas.monitoring import EvaluationIn, ObservationIn, PlanIn
from app.services import monitoring
from app.services.assurance import snapshot

router = APIRouter(prefix="/monitoring", tags=["Monitoring and evaluation"])


def output(row):
    return dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")


@router.get("/plans")
def plans(db: Session = Depends(get_db)):
    return [output(x) for x in db.scalars(select(MeasurementPlan).order_by(MeasurementPlan.id))]


@router.put("/plans/{ref}")
def plan(
    ref: str, payload: PlanIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = invoke(monitoring.plan, db, ref, payload, actor)
    commit(db)
    return output(row)


@router.get("/observations")
def observations(db: Session = Depends(get_db)):
    return [
        output(x)
        for x in db.scalars(
            select(MonitoringObservation).order_by(MonitoringObservation.period_end)
        )
    ]


@router.post("/plans/{ref}/observations", status_code=201)
def observe(
    ref: str,
    payload: ObservationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    plan = require(
        db.scalar(
            select(MeasurementPlan)
            .join(KriDefinition)
            .where(KriDefinition.kri_ref == ref)
            .with_for_update()
        )
    )
    row = invoke(monitoring.observe, db, plan, payload, actor)
    commit(db)
    return output(row)


@router.post("/observations/{observation_id}/evaluate")
def evaluate(
    observation_id: int,
    payload: EvaluationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = require(
        db.scalar(
            select(MonitoringObservation)
            .where(MonitoringObservation.id == observation_id)
            .with_for_update()
        )
    )
    invoke(monitoring.evaluate, db, row, payload, actor)
    commit(db)
    return output(row)


@router.get("/risks/{ref}/history")
def history(ref: str, db: Session = Depends(get_db)):
    risk = require(db.scalar(select(Risk).where(Risk.risk_ref == ref)))
    return [
        output(x)
        for x in db.scalars(
            select(RiskAssessmentSnapshot)
            .where(RiskAssessmentSnapshot.risk_id == risk.id)
            .order_by(RiskAssessmentSnapshot.id)
        )
    ]
