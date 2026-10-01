from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.routes.context import commit
from app.core.config import get_settings
from app.db.session import get_db
from app.models.maintenance import RetentionState
from app.schemas.maintenance import MaintenancePolicyOut
from app.services import retention
from app.services.assurance import snapshot

router = APIRouter(prefix="/maintenance", tags=["Maintenance policy"])


@router.get("/policy", response_model=MaintenancePolicyOut)
def policy(db: Session = Depends(get_db)):
    settings = get_settings()
    row = db.get(RetentionState, 1)
    return dict(
        ai_retention_days=settings.ai_retention_days,
        ai_request_limit=settings.ai_request_limit,
        ai_rate_window_seconds=settings.ai_rate_window_seconds,
        ai_concurrency_limit=settings.ai_concurrency_limit,
        retention_state=snapshot(row) if row else None,
    )


@router.post("/prune-ai", dependencies=[Depends(require_admin)])
def prune(db: Session = Depends(get_db)):
    count = retention.prune(db)
    commit(db)
    return {"deleted": count, "scope": "AI interaction diagnostics only"}
