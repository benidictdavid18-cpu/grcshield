from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.framework import FrameworkControl

router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness plus a seed check.

    A green database connection is not enough: an empty control library looks fine
    to a load balancer and useless to a user. The check reports whether the ISO
    catalogue actually holds its 93 rows.
    """
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError:
        database_ok = False

    annex_a_count = 0
    if database_ok:
        annex_a_count = db.scalar(
            select(func.count(FrameworkControl.id)).where(FrameworkControl.control_ref.like("A.%"))
        ) or 0

    seeded = annex_a_count == 93
    return {
        "status": "ok" if database_ok and seeded else "degraded",
        "database": "ok" if database_ok else "unavailable",
        "annex_a_controls": annex_a_count,
        "annex_a_expected": 93,
        "seeded": seeded,
        "environment": settings.environment,
        "disclaimer": settings.data_disclaimer,
    }
