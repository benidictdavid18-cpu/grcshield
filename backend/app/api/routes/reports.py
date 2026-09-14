
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.metrics import list_kris
from app.core import clock
from app.db.session import get_db
from app.models.privacy import RiskException
from app.models.risk import Risk, RiskAppetiteThreshold
from app.reports.executive_report import render_executive_summary
from app.reports.registry import REPORTS
from app.reports.risk_register_report import render_risk_register
from app.schemas.report import ReportOut
from app.services import executive as executive_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports() -> list[ReportOut]:
    """The three reports GRCShield produces.

    Reports whose data does not exist yet are returned with ``implemented=false``
    rather than hidden, so the UI can say what is coming and why.
    """
    return [
        ReportOut(
            code=r.code.value,
            title=r.title,
            audience=r.audience,
            decision_supported=r.decision_supported,
            available_from_phase=r.available_from_phase,
            implemented=r.implemented,
            endpoint=r.endpoint,
        )
        for r in REPORTS
    ]


@router.get("/risk-register.pdf")
def risk_register_pdf(db: Session = Depends(get_db)) -> Response:
    """Risk Register Report — for risk owners and the management review."""
    risks = db.scalars(select(Risk)).unique().all()
    thresholds = {t.category: t for t in db.scalars(select(RiskAppetiteThreshold)).all()}
    exceptions = db.scalars(select(RiskException)).all()
    pdf = render_risk_register(risks, thresholds, exceptions, clock.today())
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="finflow-risk-register.pdf"'},
    )


@router.get("/executive-summary.pdf")
def executive_summary_pdf(db: Session = Depends(get_db)) -> Response:
    """Executive Summary Report — for founders and the board."""
    # The service output is used directly rather than the serialised response model:
    # the renderer wants the TopRisk and Priority dataclasses, not dicts.
    pdf = render_executive_summary(
        executive_service.build(db, clock.today()), list_kris(db), clock.today()
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="finflow-executive-summary.pdf"'},
    )
