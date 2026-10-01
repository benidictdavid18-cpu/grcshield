from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.core.config import get_settings
from app.models.ai import AiInteraction
from app.models.maintenance import RetentionState


def prune(db, now=None):
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=get_settings().ai_retention_days)
    result = db.execute(delete(AiInteraction).where(AiInteraction.created_at < cutoff))
    row = db.get(RetentionState, 1)
    if row is None:
        row = RetentionState(id=1)
        db.add(row)
    row.last_run, row.cutoff, row.deleted_count = now, cutoff, result.rowcount
    row.policy = f"AI diagnostics: {get_settings().ai_retention_days} days. GRC audit history retained separately."
    return result.rowcount
