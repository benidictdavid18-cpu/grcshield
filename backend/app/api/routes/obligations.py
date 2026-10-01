from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
from app.api.routes.provenance import require
from app.db.session import get_db
from app.models.obligations import Obligation, ObligationDecision
from app.models.user import User
from app.schemas.obligations import DecisionIn, ObligationIn
from app.services import obligations
from app.services.people import snapshot

router = APIRouter(prefix="/obligations", tags=["Applicable obligations"])


def output(row):
    return dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")


def find(db, ref):
    return require(
        db.scalar(select(Obligation).where(Obligation.obligation_ref == ref).with_for_update())
    )


@router.get("")
def listing(db: Session = Depends(get_db)):
    return [output(x) for x in db.scalars(select(Obligation).order_by(Obligation.obligation_ref))]


@router.get("/{ref}")
def detail(ref: str, db: Session = Depends(get_db)):
    return output(find(db, ref))


@router.put("/{ref}")
def save(
    ref: str,
    payload: ObligationIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = authorized(obligations.save, db, ref, payload, actor)
    commit(db)
    return output(row)


@router.get("/{ref}/decisions")
def history(ref: str, db: Session = Depends(get_db)):
    row = find(db, ref)
    return [
        output(x)
        for x in db.scalars(
            select(ObligationDecision)
            .where(ObligationDecision.obligation_id == row.id)
            .order_by(ObligationDecision.id)
        )
    ]


@router.post("/{ref}/decisions", status_code=201)
def decide(
    ref: str,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
):
    row = authorized(obligations.decide, db, find(db, ref), payload, actor)
    commit(db)
    return output(row)
