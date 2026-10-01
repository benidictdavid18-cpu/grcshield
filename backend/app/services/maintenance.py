"""Periodic maintenance uses the same durable outbox as an explicit operator run."""

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services import notifications, retention

logger = logging.getLogger("grcshield.maintenance")


def run_once():
    with SessionLocal() as db:
        result = notifications.run(db)
        result['ai_diagnostics_pruned'] = retention.prune(db)
        db.commit()
        return result


async def worker():
    while True:
        await asyncio.sleep(get_settings().maintenance_interval_seconds)
        try:
            result = await asyncio.to_thread(run_once)
            logger.info("In-app reminder scan completed: %s", result)
        except Exception as exc:
            # No record bodies, connection strings or provider responses enter this log.
            logger.error(
                "Maintenance run failed (%s); the next cycle will retry.", type(exc).__name__
            )
