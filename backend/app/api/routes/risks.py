from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.risk import (
    Control,
    ControlAnnexALink,
    Risk,
    RiskAppetiteThreshold,
    RiskControl,
)
from app.schemas.risk import (
    AppetiteComparisonOut,
    AppetiteOut,
    BandBoundaryOut,
    LinkedControlOut,
    RegisterSummaryOut,
    ResidualUpdateIn,
    RiskDetailOut,
    RiskSummaryOut,
    ScoreOut,
)
from app.services.risk_scoring import (
    CATEGORY_LABELS,
    RiskBand,
    RiskCategory,
    band_boundaries,
)

router = APIRouter(tags=["risk"])

TODO_MARKER = "TODO AUTHOR:BENNY"


def _load_thresholds(db: Session) -> dict[RiskCategory, RiskAppetiteThreshold]:
    rows = db.scalars(select(RiskAppetiteThreshold)).all()
    return {row.category: row for row in rows}


def _risk_query():
    """Risks with their control links and each link's control eagerly loaded.

    Every response shape needs the control chain, so loading it lazily would issue a
    query per risk per control on the register page.
    """
    return select(Risk).options(
        selectinload(Risk.control_links)
        .selectinload(RiskControl.control)
        .selectinload(Control.annex_a_links)
        .selectinload(ControlAnnexALink.framework_control)
    )


def _score_out(likelihood: int, impact: int, score: int, band: RiskBand) -> ScoreOut:
    return ScoreOut(likelihood=likelihood, impact=impact, score=score, band=band)


def _summary(risk: Risk, thresholds: dict[RiskCategory, RiskAppetiteThreshold]) -> RiskSummaryOut:
    threshold = thresholds.get(risk.category)
    return RiskSummaryOut(
        risk_ref=risk.risk_ref,
        title=risk.title,
        category=risk.category,
        category_label=CATEGORY_LABELS[risk.category],
        owner_role=risk.owner_role,
        status=risk.status,
        treatment_decision=risk.treatment_decision,
        inherent=_score_out(
            risk.inherent_likelihood, risk.inherent_impact, risk.inherent_score, risk.inherent_band
        ),
        residual=_score_out(
            risk.residual_likelihood, risk.residual_impact, risk.residual_score, risk.residual_band
        ),
        appetite=AppetiteComparisonOut(
            max_acceptable_band=threshold.max_acceptable_band if threshold else None,
            approver_role=threshold.approver_role if threshold else None,
            exceeds_appetite=risk.exceeds(threshold),
        ),
        justification_outstanding=TODO_MARKER in risk.residual_justification,
        has_uncredited_controls=bool(risk.uncredited_control_links),
    )


@router.get("/risk-appetite", response_model=list[AppetiteOut])
def list_appetite(db: Session = Depends(get_db)) -> list[AppetiteOut]:
    rows = db.scalars(select(RiskAppetiteThreshold)).all()
    ordered = sorted(rows, key=lambda row: list(RiskCategory).index(row.category))
    return [
        AppetiteOut(
            category=row.category,
            category_label=CATEGORY_LABELS[row.category],
            max_acceptable_band=row.max_acceptable_band,
            approver_role=row.approver_role,
            rationale=row.rationale,
            last_reviewed=row.last_reviewed,
        )
        for row in ordered
    ]


@router.get("/risks", response_model=list[RiskSummaryOut])
def list_risks(
    category: RiskCategory | None = Query(default=None),
    exceeding_appetite: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RiskSummaryOut]:
    stmt = _risk_query().order_by(Risk.risk_ref)
    if category is not None:
        stmt = stmt.where(Risk.category == category)

    thresholds = _load_thresholds(db)
    risks = db.scalars(stmt).unique().all()
    summaries = [_summary(risk, thresholds) for risk in risks]
    if exceeding_appetite is not None:
        summaries = [s for s in summaries if s.appetite.exceeds_appetite is exceeding_appetite]
    return summaries


@router.get("/risks/summary", response_model=RegisterSummaryOut)
def register_summary(db: Session = Depends(get_db)) -> RegisterSummaryOut:
    thresholds = _load_thresholds(db)
    risks = db.scalars(_risk_query()).unique().all()
    summaries = [_summary(risk, thresholds) for risk in risks]
    band_counts = Counter(s.residual.band.value for s in summaries)
    return RegisterSummaryOut(
        total=len(summaries),
        by_residual_band={band.value: band_counts.get(band.value, 0) for band in RiskBand},
        exceeding_appetite=sum(1 for s in summaries if s.appetite.exceeds_appetite),
        justifications_outstanding=sum(1 for s in summaries if s.justification_outstanding),
        bands=[BandBoundaryOut(**b) for b in band_boundaries()],
    )


def _get_risk_or_404(db: Session, risk_ref: str) -> Risk:
    risk = db.scalar(_risk_query().where(Risk.risk_ref == risk_ref.upper()))
    if risk is None:
        raise HTTPException(status_code=404, detail=f"Unknown risk '{risk_ref}'")
    return risk


def _detail(risk: Risk, thresholds: dict[RiskCategory, RiskAppetiteThreshold]) -> RiskDetailOut:
    base = _summary(risk, thresholds)
    return RiskDetailOut(
        **base.model_dump(),
        description=risk.description,
        asset=risk.asset,
        threat=risk.threat,
        vulnerability=risk.vulnerability,
        residual_justification=risk.residual_justification,
        treatment_summary=risk.treatment_summary,
        date_identified=risk.date_identified,
        last_reviewed=risk.last_reviewed,
        next_review=risk.next_review,
        controls=[
            LinkedControlOut(
                control_id=link.control.control_id,
                title=link.control.title,
                control_family=link.control.control_family,
                owner_role=link.control.owner_role,
                annex_a_refs=link.control.annex_a_refs,
                effectiveness_basis=link.effectiveness_basis,
                credits_reduction=link.credits_reduction,
                note=link.note,
            )
            for link in sorted(risk.control_links, key=lambda link: link.control.control_id)
        ],
    )


@router.get("/risks/{risk_ref}", response_model=RiskDetailOut)
def get_risk(risk_ref: str, db: Session = Depends(get_db)) -> RiskDetailOut:
    risk = _get_risk_or_404(db, risk_ref)
    return _detail(risk, _load_thresholds(db))


@router.patch("/risks/{risk_ref}/residual", response_model=RiskDetailOut)
def update_residual(
    risk_ref: str, payload: ResidualUpdateIn, db: Session = Depends(get_db)
) -> RiskDetailOut:
    """Re-score residual risk.

    Two rules are enforced here rather than left to the analyst's discipline:

    1. A residual score must carry a written justification. Pydantic rejects an empty
       or whitespace-only string with a 422 before this body runs.
    2. A claimed reduction must be attributable to a control that has actually been
       assessed. If residual would fall below inherent while every linked control is
       untested or tested ineffective, the write is refused.
    """
    risk = _get_risk_or_404(db, risk_ref)

    proposed_score = payload.residual_likelihood * payload.residual_impact
    if proposed_score < risk.inherent_score and not risk.crediting_control_links:
        linked = len(risk.control_links)
        detail = (
            f"Residual score {proposed_score} is below the inherent score "
            f"{risk.inherent_score}, but no linked control may be credited with that "
            "reduction. "
        )
        detail += (
            f"All {linked} linked control(s) are NOT_TESTED or TESTED_INEFFECTIVE."
            if linked
            else "No controls are linked to this risk."
        )
        detail += (
            " Test a control and record the result, or score the residual at the inherent "
            "level and explain why in the justification."
        )
        raise HTTPException(status_code=422, detail=detail)

    risk.residual_likelihood = payload.residual_likelihood
    risk.residual_impact = payload.residual_impact
    risk.residual_justification = payload.residual_justification
    db.commit()
    db.refresh(risk)
    return _detail(risk, _load_thresholds(db))
