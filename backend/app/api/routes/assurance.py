from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
from app.api.routes.isms import _nonconformity_out
from app.api.routes.provenance import require
from app.db.session import get_db
from app.models.assurance import (
    AssuranceAction,
    AssuranceCycle,
    AssuranceInput,
    AuditProgramme,
    CorrectiveVerification,
)
from app.models.audit import Nonconformity
from app.models.user import User
from app.schemas.assurance import (
    ActionIn,
    ActionOut,
    AuditIn,
    CompletionIn,
    CycleOut,
    InputIn,
    InputOut,
    NonconformityIn,
    ProgrammeIn,
    ProgrammeOut,
    ReviewIn,
    VerificationIn,
    VerificationOut,
)
from app.schemas.audit import NonconformityOut
from app.services import assurance

router = APIRouter(prefix="/isms/assurance", tags=["Maintained assurance workflows"])


def cycle(db, ref):
    return require(
        db.scalar(select(AssuranceCycle).where(AssuranceCycle.cycle_ref == ref).with_for_update())
    )


@router.get("/programmes", response_model=list[ProgrammeOut])
def programmes(db: Session = Depends(get_db)):
    return db.scalars(select(AuditProgramme).order_by(AuditProgramme.programme_ref)).all()


@router.put("/programmes/{ref}", response_model=ProgrammeOut)
def programme(
    ref: str,
    payload: ProgrammeIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = authorized(assurance.programme, db, ref, payload, actor)
    commit(db)
    return row


@router.get("/cycles", response_model=list[CycleOut])
def cycles(db: Session = Depends(get_db)):
    return db.scalars(select(AssuranceCycle).order_by(AssuranceCycle.cycle_ref)).all()


@router.get("/cycles/{ref}", response_model=CycleOut)
def detail(ref: str, db: Session = Depends(get_db)):
    return cycle(db, ref)


@router.put("/audits/{ref}", response_model=CycleOut)
def audit(
    ref: str, payload: AuditIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = authorized(assurance.cycle, db, ref, payload, actor, "AUDIT")
    commit(db)
    return row


@router.put("/reviews/{ref}", response_model=CycleOut)
def review(
    ref: str, payload: ReviewIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = authorized(assurance.cycle, db, ref, payload, actor, "REVIEW")
    commit(db)
    return row


@router.get("/review-input-categories", response_model=list[str])
def categories():
    return list(assurance.REVIEW_INPUTS)


@router.get("/cycles/{ref}/inputs", response_model=list[InputOut])
def inputs(ref: str, db: Session = Depends(get_db)):
    return db.scalars(
        select(AssuranceInput).where(AssuranceInput.cycle_id == cycle(db, ref).id)
    ).all()


@router.put("/cycles/{ref}/inputs/{category}", response_model=InputOut)
def input_record(
    ref: str,
    category: str,
    payload: InputIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = authorized(assurance.input_record, db, cycle(db, ref), category, payload, actor)
    commit(db)
    return row


@router.get("/cycles/{ref}/actions", response_model=list[ActionOut])
def actions(ref: str, db: Session = Depends(get_db)):
    return db.scalars(
        select(AssuranceAction).where(AssuranceAction.cycle_id == cycle(db, ref).id)
    ).all()


@router.post("/cycles/{ref}/actions", response_model=ActionOut, status_code=201)
def action(
    ref: str, payload: ActionIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = authorized(assurance.action, db, cycle(db, ref), payload, actor)
    commit(db)
    return row


@router.post("/cycles/{ref}/complete", response_model=CycleOut)
def complete(
    ref: str,
    payload: CompletionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = cycle(db, ref)
    authorized(assurance.complete, db, row, payload, actor)
    commit(db)
    return row


@router.post("/actions/{ref}/complete", response_model=ActionOut)
def complete_action(
    ref: str,
    payload: CompletionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = require(
        db.scalar(
            select(AssuranceAction).where(AssuranceAction.action_ref == ref).with_for_update()
        )
    )
    authorized(assurance.complete_action, db, row, payload, actor)
    commit(db)
    return row


@router.put("/nonconformities/{ref}", response_model=NonconformityOut)
def nonconformity(
    ref: str,
    payload: NonconformityIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = authorized(assurance.nonconformity, db, ref, payload, actor)
    commit(db)
    return _nonconformity_out(row)


@router.get("/nonconformities/{ref}/verifications", response_model=list[VerificationOut])
def verifications(ref: str, db: Session = Depends(get_db)):
    row = require(db.scalar(select(Nonconformity).where(Nonconformity.nc_ref == ref)))
    return db.scalars(
        select(CorrectiveVerification)
        .where(CorrectiveVerification.nonconformity_id == row.id)
        .order_by(CorrectiveVerification.id)
    ).all()


@router.post(
    "/nonconformities/{ref}/verifications", response_model=VerificationOut, status_code=201
)
def verify(
    ref: str,
    payload: VerificationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = require(
        db.scalar(select(Nonconformity).where(Nonconformity.nc_ref == ref).with_for_update())
    )
    result = authorized(assurance.verify, db, row, payload, actor)
    commit(db)
    return result
