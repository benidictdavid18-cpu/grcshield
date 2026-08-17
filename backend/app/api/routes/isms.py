"""ISO/IEC 27001:2022 clause-level records: 9.2, 9.3 and 10.2.

Kept deliberately lightweight — list, detail, export. These records exist because a
certification auditor will ask for them, not because they need a rich interface.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.audit import InternalAudit, ManagementReview, Nonconformity
from app.reports.isms_report import render_isms_records
from app.schemas.audit import (
    InternalAuditOut,
    ManagementReviewOut,
    NonconformityOut,
)

router = APIRouter(prefix="/isms", tags=["ISMS clause records"])


@router.get("/audits", response_model=list[InternalAuditOut])
def list_audits(db: Session = Depends(get_db)) -> list[InternalAudit]:
    """Clause 9.2 — internal audit programme."""
    return list(db.scalars(select(InternalAudit).order_by(InternalAudit.audit_ref)).all())


@router.get("/audits/{audit_ref}", response_model=InternalAuditOut)
def get_audit(audit_ref: str, db: Session = Depends(get_db)) -> InternalAudit:
    audit = db.scalar(select(InternalAudit).where(InternalAudit.audit_ref == audit_ref.upper()))
    if audit is None:
        raise HTTPException(status_code=404, detail=f"Unknown audit '{audit_ref}'")
    return audit


@router.get("/management-reviews", response_model=list[ManagementReviewOut])
def list_management_reviews(db: Session = Depends(get_db)) -> list[ManagementReview]:
    """Clause 9.3 — management review."""
    return list(
        db.scalars(select(ManagementReview).order_by(ManagementReview.review_date.desc())).all()
    )


@router.get("/management-reviews/{review_ref}", response_model=ManagementReviewOut)
def get_management_review(review_ref: str, db: Session = Depends(get_db)) -> ManagementReview:
    review = db.scalar(
        select(ManagementReview).where(ManagementReview.review_ref == review_ref.upper())
    )
    if review is None:
        raise HTTPException(status_code=404, detail=f"Unknown review '{review_ref}'")
    return review


def _nonconformity_out(nc: Nonconformity) -> NonconformityOut:
    return NonconformityOut(
        nc_ref=nc.nc_ref,
        description=nc.description,
        source=nc.source,
        identified_date=nc.identified_date,
        identified_by=nc.identified_by,
        owner=nc.owner,
        immediate_correction=nc.immediate_correction,
        root_cause_analysis=nc.root_cause_analysis,
        corrective_action=nc.corrective_action,
        target_date=nc.target_date,
        effectiveness_check_date=nc.effectiveness_check_date,
        effectiveness_check_result=nc.effectiveness_check_result,
        status=nc.status,
        closure_date=nc.closure_date,
        finding_ref=nc.finding.finding_ref if nc.finding else None,
    )


@router.get("/nonconformities", response_model=list[NonconformityOut])
def list_nonconformities(db: Session = Depends(get_db)) -> list[NonconformityOut]:
    """Clause 10.2 — nonconformity and corrective action."""
    rows = db.scalars(
        select(Nonconformity)
        .options(selectinload(Nonconformity.finding))
        .order_by(Nonconformity.nc_ref)
    ).all()
    return [_nonconformity_out(nc) for nc in rows]


@router.get("/nonconformities/{nc_ref}", response_model=NonconformityOut)
def get_nonconformity(nc_ref: str, db: Session = Depends(get_db)) -> NonconformityOut:
    nc = db.scalar(
        select(Nonconformity)
        .options(selectinload(Nonconformity.finding))
        .where(Nonconformity.nc_ref == nc_ref.upper())
    )
    if nc is None:
        raise HTTPException(status_code=404, detail=f"Unknown nonconformity '{nc_ref}'")
    return _nonconformity_out(nc)


@router.get("/records.pdf")
def isms_records_pdf(db: Session = Depends(get_db)) -> Response:
    """Export of the Clause 9.2 / 9.3 / 10.2 records.

    Deliberately **not** one of the three reports in the report registry. Those three
    each support a named decision for a named audience. This is a records export — the
    bundle an auditor asks for when they want to read what actually happened — and
    conflating the two would put a fourth entry in a report set that was cut to three
    on purpose.
    """
    audits = list(db.scalars(select(InternalAudit).order_by(InternalAudit.audit_ref)).all())
    reviews = list(
        db.scalars(select(ManagementReview).order_by(ManagementReview.review_date)).all()
    )
    ncs = list(
        db.scalars(
            select(Nonconformity)
            .options(selectinload(Nonconformity.finding))
            .order_by(Nonconformity.nc_ref)
        ).all()
    )
    pdf = render_isms_records(audits, reviews, ncs)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="finflow-isms-records.pdf"'},
    )
