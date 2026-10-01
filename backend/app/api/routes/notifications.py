from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_write
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
from app.api.routes.provenance import require
from app.db.session import get_db
from app.models.notifications import Notification, NotificationRouting
from app.models.user import User
from app.schemas.notifications import RouteIn
from app.services import notifications
from app.services.assurance import snapshot

router = APIRouter(prefix="/notifications", tags=["In-app notifications"])


@router.get("")
def listing(db: Session = Depends(get_db), actor: User = Depends(current_user)):
    return [
        dict(snapshot(row), disclaimer="Sample / Portfolio Assessment")
        for row in db.scalars(
            select(Notification)
            .where(Notification.user_id == actor.id)
            .order_by(Notification.id.desc())
        )
    ]


@router.get("/outbox", dependencies=[Depends(require_write)])
def outbox(db: Session = Depends(get_db)):
    return [
        snapshot(row) for row in db.scalars(select(Notification).order_by(Notification.id.desc()))
    ]


@router.get("/routing", dependencies=[Depends(require_write)])
def routes(db: Session = Depends(get_db)):
    return [snapshot(row) for row in db.scalars(select(NotificationRouting))]


@router.put("/routing", dependencies=[Depends(require_write)])
def route(payload: RouteIn, db: Session = Depends(get_db), actor: User = Depends(current_user)):
    row = authorized(notifications.route, db, payload, actor)
    commit(db)
    return snapshot(row)


@router.post("/run", dependencies=[Depends(require_write)])
def run(db: Session = Depends(get_db)):
    result = notifications.run(db)
    commit(db)
    return result


@router.post("/{notification_id}/acknowledge")
def acknowledge(
    notification_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)
):
    row = require(
        db.scalar(select(Notification).where(Notification.id == notification_id).with_for_update())
    )
    authorized(notifications.acknowledge, db, row, actor)
    commit(db)
    return snapshot(row)
