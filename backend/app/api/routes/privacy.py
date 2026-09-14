"""Risk acceptance, GDPR records (Articles 30 and 35) and business impact analysis."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user
from app.core import clock
from app.db.session import get_db
from app.models.audit_trail import AuditAction
from app.models.privacy import (
    Asset,
    BiaAssetLink,
    BiaControlLink,
    BiaRiskLink,
    BusinessImpactAnalysis,
    Dpia,
    DpiaAssetLink,
    DpiaRiskLink,
    RiskException,
    RopaAssetLink,
    RopaControlLink,
    RopaEntry,
    RopaRiskLink,
)
from app.models.risk import Risk, RiskAppetiteThreshold
from app.models.user import User
from app.schemas.privacy import (
    AssetOut,
    BiaOut,
    ControlBrief,
    DpiaOut,
    ExceptionCreateIn,
    ExceptionOut,
    ExceptionSummaryOut,
    LinkedRiskBrief,
    PrivacyOverviewOut,
    RopaOut,
)
from app.services import audit_trail
from app.services.control_testing import OperatingEffectiveness
from app.services.privacy_continuity import (
    EXPIRY_WARNING_DAYS,
    DpiaOutcome,
    LawfulBasis,
    ResidualRiskLevel,
    validate_exception,
)

router = APIRouter(tags=["privacy and continuity"])


def _today() -> date:
    return clock.today()


def _thresholds(db: Session) -> dict:
    return {row.category: row for row in db.scalars(select(RiskAppetiteThreshold)).all()}


def _risk_brief(risk: Risk, thresholds: dict) -> LinkedRiskBrief:
    return LinkedRiskBrief(
        risk_ref=risk.risk_ref,
        title=risk.title,
        residual_score=risk.residual_score,
        residual_band=risk.residual_band,
        exceeds_appetite=risk.exceeds(thresholds.get(risk.category)),
    )


def _control_brief(control) -> ControlBrief:
    """`credited` answers whether the measure is currently known to work.

    A RoPA entry listing a security measure that failed its last test is claiming
    protection it does not have — ROPA-003 lists DP-005, which TEST-008 rated
    INEFFECTIVE. That should be visible on the record rather than buried in the control
    library.
    """
    return ControlBrief(
        control_id=control.control_id,
        title=control.title,
        operating_effectiveness=control.operating_effectiveness.value,
        credited=control.operating_effectiveness
        in (OperatingEffectiveness.EFFECTIVE, OperatingEffectiveness.EFFECTIVE_WITH_EXCEPTIONS),
    )


def _asset_out(asset: Asset) -> AssetOut:
    return AssetOut.model_validate(asset)


# --- Assets ---------------------------------------------------------------------


@router.get("/assets", response_model=list[AssetOut])
def list_assets(
    holds_personal_data: bool | None = Query(default=None), db: Session = Depends(get_db)
) -> list[AssetOut]:
    stmt = select(Asset).order_by(Asset.sort_order)
    if holds_personal_data is not None:
        stmt = stmt.where(Asset.holds_personal_data.is_(holds_personal_data))
    return [_asset_out(a) for a in db.scalars(stmt).all()]


# --- Risk acceptance --------------------------------------------------------------


def _exception_query():
    return select(RiskException).options(selectinload(RiskException.risk))


def _exception_out(exception: RiskException, thresholds: dict, as_of: date) -> ExceptionOut:
    risk = exception.risk
    return ExceptionOut(
        exception_ref=exception.exception_ref,
        risk_ref=risk.risk_ref,
        risk_title=risk.title,
        risk_owner_role=risk.owner_role,
        residual_band=risk.residual_band,
        exceeds_appetite=risk.exceeds(thresholds.get(risk.category)),
        requested_by=exception.requested_by,
        business_justification=exception.business_justification,
        compensating_controls=exception.compensating_controls,
        approver_role=exception.approver_role,
        approval_date=exception.approval_date,
        expiry_date=exception.expiry_date,
        review_trigger=exception.review_trigger,
        status=exception.status,
        state=exception.state(as_of),
        days_remaining=exception.days_remaining(as_of),
        decision_note=exception.decision_note,
    )


@router.get("/risk-exceptions", response_model=list[ExceptionOut])
def list_exceptions(
    state: str | None = Query(default=None, description="EXPIRED, EXPIRING_SOON, APPROVED..."),
    db: Session = Depends(get_db),
) -> list[ExceptionOut]:
    as_of = _today()
    thresholds = _thresholds(db)
    rows = db.scalars(_exception_query().order_by(RiskException.exception_ref)).unique().all()
    out = [_exception_out(row, thresholds, as_of) for row in rows]
    if state:
        out = [row for row in out if row.state == state.upper()]
    return out


@router.get("/risk-exceptions/summary", response_model=ExceptionSummaryOut)
def exception_summary(db: Session = Depends(get_db)) -> ExceptionSummaryOut:
    """Dashboard counts, plus the gap nobody asks for.

    ``uncovered_breaches`` lists risks sitting above their category appetite with no
    live acceptance covering them. Those are exposures being carried without anyone
    having decided to carry them, which is worse than a documented acceptance.
    """
    as_of = _today()
    thresholds = _thresholds(db)
    rows = db.scalars(_exception_query()).unique().all()
    states = [row.state(as_of) for row in rows]

    covered = {
        row.risk.risk_ref
        for row in rows
        if row.state(as_of) in ("APPROVED", "PENDING", "EXPIRING_SOON")
    }
    breaching = {
        risk.risk_ref
        for risk in db.scalars(select(Risk)).all()
        if risk.exceeds(thresholds.get(risk.category))
    }

    return ExceptionSummaryOut(
        total=len(rows),
        live=sum(1 for s in states if s in ("APPROVED", "PENDING")),
        expired=sum(1 for s in states if s == "EXPIRED"),
        expiring_soon=sum(1 for s in states if s == "EXPIRING_SOON"),
        rejected_or_withdrawn=sum(1 for s in states if s in ("REJECTED", "WITHDRAWN")),
        expiry_warning_days=EXPIRY_WARNING_DAYS,
        uncovered_breaches=sorted(breaching - covered),
    )


@router.post("/risk-exceptions", response_model=ExceptionOut, status_code=201)
def create_exception(
    payload: ExceptionCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ExceptionOut:
    """Record a risk acceptance.

    Two rules an acceptance register exists to enforce:

    1. **It must expire.** An acceptance with no end date is a permanent decision
       disguised as a temporary one.
    2. **The approver must be the risk owner** (or a named escalation approver), and
       never the security function. Security advises on risk; the business decides to
       carry it. An acceptance signed by the people who raised the risk is not an
       acceptance.
    """
    risk = db.scalar(select(Risk).where(Risk.risk_ref == payload.risk_ref.upper()))
    if risk is None:
        raise HTTPException(status_code=404, detail=f"Unknown risk '{payload.risk_ref}'")

    errors = validate_exception(
        approver_role=payload.approver_role,
        risk_owner_role=risk.owner_role,
        expiry_date=payload.expiry_date,
        approval_date=payload.approval_date,
        business_justification=payload.business_justification,
        review_trigger=payload.review_trigger,
        status=payload.status,
    )
    if errors:
        raise HTTPException(
            status_code=422,
            detail=[{"field": e.field, "message": e.message} for e in errors],
        )

    existing = db.scalars(select(RiskException.exception_ref)).all()
    numbers = [int(ref.split("-")[-1]) for ref in existing if ref.split("-")[-1].isdigit()]
    exception = RiskException(
        exception_ref=f"EXC-{max(numbers, default=0) + 1:03d}",
        risk_id=risk.id,
        requested_by=payload.requested_by,
        business_justification=payload.business_justification,
        compensating_controls=payload.compensating_controls,
        approver_role=payload.approver_role,
        approval_date=payload.approval_date,
        expiry_date=payload.expiry_date,
        review_trigger=payload.review_trigger,
        status=payload.status,
    )
    db.add(exception)
    db.flush()
    audit_trail.record_change(
        db,
        actor=user,
        action=AuditAction.RISK_EXCEPTION_RECORDED,
        record_type="RISK_EXCEPTION",
        record_ref=exception.exception_ref,
        before=None,
        after={
            "risk_ref": risk.risk_ref,
            "requested_by": payload.requested_by,
            "approver_role": payload.approver_role,
            "approval_date": payload.approval_date,
            "expiry_date": payload.expiry_date,
            "status": payload.status,
        },
        summary=(
            f"{exception.exception_ref} recorded for {risk.risk_ref}: "
            f"{payload.status.value}, approver {payload.approver_role}, "
            f"expires {payload.expiry_date.isoformat()}."
        ),
    )
    db.commit()
    db.refresh(exception)
    return _exception_out(exception, _thresholds(db), _today())


# --- GDPR: Article 30 ---------------------------------------------------------------


def _ropa_query():
    return select(RopaEntry).options(
        selectinload(RopaEntry.asset_links).selectinload(RopaAssetLink.asset),
        selectinload(RopaEntry.risk_links).selectinload(RopaRiskLink.risk),
        selectinload(RopaEntry.control_links).selectinload(RopaControlLink.control),
    )


def _ropa_out(entry: RopaEntry, thresholds: dict, dpia_refs: list[str]) -> RopaOut:
    return RopaOut(
        ropa_ref=entry.ropa_ref,
        processing_activity=entry.processing_activity,
        purpose=entry.purpose,
        lawful_basis=entry.lawful_basis,
        legitimate_interests_assessment=entry.legitimate_interests_assessment,
        data_subject_categories=entry.data_subject_categories,
        personal_data_categories=entry.personal_data_categories,
        special_category_data=entry.special_category_data,
        recipients=entry.recipients,
        transfers_outside_eea=entry.transfers_outside_eea,
        transfer_detail=entry.transfer_detail,
        transfer_safeguard=entry.transfer_safeguard,
        retention_period=entry.retention_period,
        security_measures_summary=entry.security_measures_summary,
        controller_role=entry.controller_role,
        owner_role=entry.owner_role,
        last_reviewed=entry.last_reviewed,
        assets=[_asset_out(a) for a in entry.linked_assets],
        risks=[_risk_brief(r, thresholds) for r in entry.linked_risks],
        controls=[_control_brief(c) for c in entry.linked_controls],
        dpia_refs=dpia_refs,
    )


@router.get("/ropa", response_model=list[RopaOut])
def list_ropa(db: Session = Depends(get_db)) -> list[RopaOut]:
    thresholds = _thresholds(db)
    entries = db.scalars(_ropa_query().order_by(RopaEntry.ropa_ref)).unique().all()
    dpia_map: dict[int, list[str]] = {}
    for dpia in db.scalars(select(Dpia)).all():
        if dpia.ropa_id:
            dpia_map.setdefault(dpia.ropa_id, []).append(dpia.dpia_ref)
    return [_ropa_out(e, thresholds, sorted(dpia_map.get(e.id, []))) for e in entries]


@router.get("/ropa/{ropa_ref}", response_model=RopaOut)
def get_ropa(ropa_ref: str, db: Session = Depends(get_db)) -> RopaOut:
    entry = db.scalar(_ropa_query().where(RopaEntry.ropa_ref == ropa_ref.upper()))
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown processing activity '{ropa_ref}'")
    refs = sorted(
        d.dpia_ref for d in db.scalars(select(Dpia).where(Dpia.ropa_id == entry.id)).all()
    )
    return _ropa_out(entry, _thresholds(db), refs)


# --- GDPR: Article 35 ---------------------------------------------------------------


def _dpia_query():
    return select(Dpia).options(
        selectinload(Dpia.ropa),
        selectinload(Dpia.asset_links).selectinload(DpiaAssetLink.asset),
        selectinload(Dpia.risk_links).selectinload(DpiaRiskLink.risk),
    )


def _dpia_out(dpia: Dpia, thresholds: dict, as_of: date) -> DpiaOut:
    return DpiaOut(
        dpia_ref=dpia.dpia_ref,
        title=dpia.title,
        ropa_ref=dpia.ropa.ropa_ref if dpia.ropa else None,
        trigger_reason=dpia.trigger_reason,
        processing_description=dpia.processing_description,
        necessity_and_proportionality=dpia.necessity_and_proportionality,
        risks_to_data_subjects=dpia.risks_to_data_subjects,
        mitigating_measures=dpia.mitigating_measures,
        residual_risk=dpia.residual_risk,
        residual_risk_note=dpia.residual_risk_note,
        dpo_consulted=dpia.dpo_consulted,
        dpo_advice=dpia.dpo_advice,
        supervisory_authority_consulted=dpia.supervisory_authority_consulted,
        data_subjects_consulted=dpia.data_subjects_consulted,
        outcome=dpia.outcome,
        assessed_by=dpia.assessed_by,
        assessment_date=dpia.assessment_date,
        review_date=dpia.review_date,
        review_overdue=dpia.review_overdue(as_of),
        assets=[_asset_out(a) for a in dpia.linked_assets],
        risks=[_risk_brief(r, thresholds) for r in dpia.linked_risks],
    )


@router.get("/dpias", response_model=list[DpiaOut])
def list_dpias(db: Session = Depends(get_db)) -> list[DpiaOut]:
    as_of = _today()
    thresholds = _thresholds(db)
    rows = db.scalars(_dpia_query().order_by(Dpia.dpia_ref)).unique().all()
    return [_dpia_out(d, thresholds, as_of) for d in rows]


@router.get("/dpias/{dpia_ref}", response_model=DpiaOut)
def get_dpia(dpia_ref: str, db: Session = Depends(get_db)) -> DpiaOut:
    dpia = db.scalar(_dpia_query().where(Dpia.dpia_ref == dpia_ref.upper()))
    if dpia is None:
        raise HTTPException(status_code=404, detail=f"Unknown DPIA '{dpia_ref}'")
    return _dpia_out(dpia, _thresholds(db), _today())


@router.get("/privacy/overview", response_model=PrivacyOverviewOut)
def privacy_overview(db: Session = Depends(get_db)) -> PrivacyOverviewOut:
    as_of = _today()
    ropa = db.scalars(select(RopaEntry)).all()
    dpias = db.scalars(select(Dpia)).all()
    assets = db.scalars(select(Asset)).all()
    return PrivacyOverviewOut(
        ropa_entries=len(ropa),
        activities_with_transfers=sum(1 for e in ropa if e.transfers_outside_eea),
        activities_on_legitimate_interests=sum(
            1 for e in ropa if e.lawful_basis == LawfulBasis.LEGITIMATE_INTERESTS
        ),
        dpias=len(dpias),
        dpias_high_residual=sum(
            1 for d in dpias if d.residual_risk == ResidualRiskLevel.HIGH
        ),
        dpias_review_overdue=sum(1 for d in dpias if d.review_overdue(as_of)),
        dpias_awaiting_supervisory_consultation=sum(
            1
            for d in dpias
            if d.outcome == DpiaOutcome.CONSULT_SUPERVISORY_AUTHORITY
            and not d.supervisory_authority_consulted
        ),
        assets=len(assets),
        assets_holding_personal_data=sum(1 for a in assets if a.holds_personal_data),
    )


# --- Business impact analysis --------------------------------------------------------


@router.get("/bia", response_model=list[BiaOut])
def list_bia(db: Session = Depends(get_db)) -> list[BiaOut]:
    thresholds = _thresholds(db)
    rows = (
        db.scalars(
            select(BusinessImpactAnalysis)
            .options(
                selectinload(BusinessImpactAnalysis.asset_links).selectinload(BiaAssetLink.asset),
                selectinload(BusinessImpactAnalysis.control_links).selectinload(
                    BiaControlLink.control
                ),
                selectinload(BusinessImpactAnalysis.risk_links).selectinload(BiaRiskLink.risk),
            )
            .order_by(BusinessImpactAnalysis.bia_ref)
        )
        .unique()
        .all()
    )
    return [
        BiaOut(
            bia_ref=bia.bia_ref,
            process_name=bia.process_name,
            process_description=bia.process_description,
            owner_role=bia.owner_role,
            rto_hours=bia.rto_hours,
            rpo_hours=bia.rpo_hours,
            mtpd_hours=bia.mtpd_hours,
            # How much slack remains between the recovery target and the point the
            # business can no longer bear the outage.
            recovery_headroom_hours=round(bia.mtpd_hours - bia.rto_hours, 2),
            currency=bia.currency,
            impact_1h=float(bia.impact_1h),
            impact_24h=float(bia.impact_24h),
            impact_1w=float(bia.impact_1w),
            impact_note=bia.impact_note,
            workaround=bia.workaround,
            recovery_note=bia.recovery_note,
            last_reviewed=bia.last_reviewed,
            assets=[_asset_out(a) for a in bia.linked_assets],
            controls=[_control_brief(c) for c in bia.linked_controls],
            risks=[_risk_brief(r, thresholds) for r in bia.linked_risks],
        )
        for bia in rows
    ]
