from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.audit import ControlTest
from app.models.provenance import Reassessment
from app.models.risk import Control, Risk, RiskControl
from app.models.soa import Evidence
from app.models.user import User
from app.schemas.provenance import DispositionIn, ProofIn, ReassessmentOut, ResolutionIn
from app.services import provenance

router = APIRouter(tags=["test provenance"])


def require(row):
    if row is None:
        raise HTTPException(404, "Record not found")
    return row


def invoke(fn, *args):
    try:
        return fn(*args)
    except provenance.ProofError as e:
        raise HTTPException(422, detail=[{"field": e.field, "message": str(e)}]) from e


@router.put("/risks/{risk_ref}/controls/{control_ref}/proof")
def bind(
    risk_ref: str,
    control_ref: str,
    payload: ProofIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    link = require(
        db.scalar(
            select(RiskControl)
            .join(Risk)
            .join(Control)
            .where(Risk.risk_ref == risk_ref, Control.control_id == control_ref)
        )
    )
    test = require(db.scalar(select(ControlTest).where(ControlTest.test_ref == payload.test_ref)))
    invoke(provenance.bind_proof, db, link, test, payload.note, user)
    db.commit()
    db.expire(link, ["supporting_test"])
    return {**provenance.proof_summary(db, link), "disclaimer": "Sample / Portfolio Assessment"}


@router.post("/control-tests/{test_ref}/disposition", status_code=201)
def disposition(
    test_ref: str,
    payload: DispositionIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    test = require(db.scalar(select(ControlTest).where(ControlTest.test_ref == test_ref)))
    replacement = (
        require(
            db.scalar(select(ControlTest).where(ControlTest.test_ref == payload.replacement_ref))
        )
        if payload.replacement_ref
        else None
    )
    item = invoke(provenance.dispose_test, db, test, replacement, payload.reason, user)
    db.commit()
    return {
        "kind": item.kind,
        "test_ref": test_ref,
        "replacement_ref": payload.replacement_ref,
        "disclaimer": "Sample / Portfolio Assessment",
    }


@router.get("/reassessments", response_model=list[ReassessmentOut])
def queue(db: Session = Depends(get_db)):
    return db.scalars(select(Reassessment).order_by(Reassessment.id)).all()


@router.post("/reassessments/{item_id}/resolve", response_model=ReassessmentOut)
def resolve(
    item_id: int,
    payload: ResolutionIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = require(db.get(Reassessment, item_id))
    evidence = require(
        db.scalar(select(Evidence).where(Evidence.evidence_ref == payload.evidence_ref))
    )
    invoke(provenance.resolve, db, item, evidence, payload.resolution, user)
    db.commit()
    return item
