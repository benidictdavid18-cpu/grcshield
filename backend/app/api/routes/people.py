from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.context import commit
from app.api.routes.provenance import invoke, require
from app.db.session import get_db
from app.models.people import CommunicationPlan, CompetenceEvaluation, CompetenceRequirement
from app.models.user import User
from app.schemas.assurance import CompletionIn
from app.schemas.people import CommunicationIn, EvaluationIn, RequirementIn
from app.services import people
from app.services.assurance import snapshot

router = APIRouter(prefix="/people", tags=["Competence and communications"])


def private(actor: User = Depends(current_user)):
    if not actor.can_write:
        raise HTTPException(403, "Personnel evaluations are restricted to maintainers.")
    return actor


def output(row):
    return dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")


def find(db, ref):
    return require(
        db.scalar(
            select(CompetenceRequirement)
            .where(CompetenceRequirement.requirement_ref == ref)
            .with_for_update()
        )
    )


@router.get("/requirements")
def requirements(db: Session = Depends(get_db)):
    return [
        output(x)
        for x in db.scalars(
            select(CompetenceRequirement).order_by(CompetenceRequirement.requirement_ref)
        )
    ]


@router.put("/requirements/{ref}")
def save(
    ref: str,
    payload: RequirementIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = invoke(people.requirement, db, ref, payload, actor)
    commit(db)
    return output(row)


@router.get("/requirements/{ref}/evaluations")
def evaluations(ref: str, db: Session = Depends(get_db), actor: User = Depends(private)):
    row = find(db, ref)
    return [
        output(x)
        for x in db.scalars(
            select(CompetenceEvaluation)
            .where(CompetenceEvaluation.requirement_id == row.id)
            .order_by(CompetenceEvaluation.id)
        )
    ]


@router.post("/requirements/{ref}/evaluations", status_code=201)
def evaluate(
    ref: str, payload: EvaluationIn, db: Session = Depends(get_db), actor: User = Depends(private)
):
    row = invoke(people.evaluate, db, find(db, ref), payload, actor)
    commit(db)
    return output(row)


@router.get("/communications")
def communications(db: Session = Depends(get_db)):
    return [
        output(x)
        for x in db.scalars(select(CommunicationPlan).order_by(CommunicationPlan.communication_ref))
    ]


@router.put("/communications/{ref}")
def communication(
    ref: str,
    payload: CommunicationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = invoke(people.communication, db, ref, payload, actor)
    commit(db)
    return output(row)


@router.post("/communications/{ref}/deliver")
def deliver(
    ref: str,
    payload: CompletionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = require(
        db.scalar(
            select(CommunicationPlan)
            .where(CommunicationPlan.communication_ref == ref)
            .with_for_update()
        )
    )
    invoke(people.deliver, db, row, payload, actor)
    commit(db)
    return output(row)
