from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.context import commit
from app.api.routes.provenance import invoke, require
from app.db.session import get_db
from app.models.incidents import IncidentEntry, SecurityEvent
from app.models.user import User
from app.schemas.incidents import EntryIn, EntryOut, EventIn, EventOut
from app.services import incidents

router = APIRouter(prefix="/incidents", tags=["Events and incidents"])


def find(db, ref):
    return require(
        db.scalar(select(SecurityEvent).where(SecurityEvent.event_ref == ref).with_for_update())
    )


@router.get("", response_model=list[EventOut])
def events(db: Session = Depends(get_db)):
    return db.scalars(select(SecurityEvent).order_by(SecurityEvent.event_ref)).all()


@router.get("/{ref}", response_model=EventOut)
def detail(ref: str, db: Session = Depends(get_db)):
    return find(db, ref)


@router.post("/{ref}", response_model=EventOut, status_code=201)
def create(
    ref: str, payload: EventIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = invoke(incidents.create, db, ref, payload, actor)
    commit(db)
    return row


@router.get("/{ref}/timeline", response_model=list[EntryOut])
def timeline(ref: str, db: Session = Depends(get_db)):
    row = find(db, ref)
    return db.scalars(
        select(IncidentEntry).where(IncidentEntry.event_id == row.id).order_by(IncidentEntry.id)
    ).all()


@router.post("/{ref}/timeline", response_model=EntryOut, status_code=201)
def append(
    ref: str, payload: EntryIn, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = invoke(incidents.append, db, find(db, ref), payload, actor)
    commit(db)
    return row
