from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.context import commit
from app.api.routes.provenance import invoke, require
from app.db.session import get_db
from app.models.operations import (
    ContinuityExercise,
    OperationalEvidence,
    OperationalReviewTask,
    RegisterRevision,
)
from app.models.user import User
from app.schemas.assurance import CompletionIn
from app.schemas.operations import CoverageIn, ExerciseIn, RevisionIn
from app.services import operations

router = APIRouter(prefix="/operations", tags=["Maintained operational registers"])


def output(row):
    return dict(operations.snapshot(row), disclaimer="Sample / Portfolio Assessment")


@router.get("/schemas")
def schemas():
    return {kind: spec[2].model_json_schema() for kind, spec in operations.KINDS.items()}


@router.get("/revisions")
def revisions(db: Session = Depends(get_db)):
    return [output(x) for x in db.scalars(select(RegisterRevision).order_by(RegisterRevision.id))]


@router.post("/revisions", status_code=201)
def propose(
    payload: RevisionIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    item = invoke(operations.propose, db, payload, actor)
    commit(db)
    return output(item)


@router.post("/revisions/{revision_id}/review")
def review(
    revision_id: int,
    payload: CompletionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    item = require(
        db.scalar(
            select(RegisterRevision).where(RegisterRevision.id == revision_id).with_for_update()
        )
    )
    invoke(operations.review, db, item, payload, actor)
    commit(db)
    return output(item)


@router.get("/reassessments")
def tasks(db: Session = Depends(get_db)):
    return [
        output(x)
        for x in db.scalars(select(OperationalReviewTask).order_by(OperationalReviewTask.id))
    ]


@router.post("/reassessments/{task_id}/resolve")
def resolve(
    task_id: int,
    payload: CompletionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = require(
        db.scalar(
            select(OperationalReviewTask)
            .where(OperationalReviewTask.id == task_id)
            .with_for_update()
        )
    )
    invoke(operations.resolve, db, row, payload, actor)
    commit(db)
    return output(row)


@router.get("/coverage")
def coverages(db: Session = Depends(get_db)):
    return [
        output(x) for x in db.scalars(select(OperationalEvidence).order_by(OperationalEvidence.id))
    ]


@router.post("/coverage", status_code=201)
def coverage(
    payload: CoverageIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = invoke(operations.coverage, db, payload, actor)
    commit(db)
    return output(row)


@router.get("/exercises")
def exercises(db: Session = Depends(get_db)):
    return [
        output(x) for x in db.scalars(select(ContinuityExercise).order_by(ContinuityExercise.id))
    ]


@router.post("/exercises/{ref}", status_code=201)
def exercise(
    ref: str,
    payload: ExerciseIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = invoke(operations.exercise, db, ref, payload, actor)
    commit(db)
    return output(row)


@router.get("/registers/{kind}")
def register(kind: Literal["ASSET", "ROPA", "DPIA", "BIA"], db: Session = Depends(get_db)):
    model, key, _ = operations.KINDS[kind]
    return [
        dict(operations.view(db, kind, x), disclaimer="Sample / Portfolio Assessment")
        for x in db.scalars(select(model).order_by(getattr(model, key)))
    ]
