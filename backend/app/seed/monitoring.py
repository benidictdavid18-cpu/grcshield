from datetime import date

from sqlalchemy import select

from app.models.kri import KriDefinition
from app.models.monitoring import MeasurementPlan

MONITORING_HINT = "TODO AUTHOR:BENNY - confirm reproducible collection method, population, source and evaluation responsibilities before recording observations."


def seed_monitoring(db):
    for kri in db.scalars(select(KriDefinition)):
        if db.scalar(select(MeasurementPlan.id).where(MeasurementPlan.kri_id == kri.id)) is None:
            db.add(
                MeasurementPlan(
                    kri_id=kri.id,
                    method=kri.formula_description + " " + MONITORING_HINT,
                    population=MONITORING_HINT,
                    source=kri.data_source,
                    collection_owner=MONITORING_HINT[:160],
                    evaluation_owner=MONITORING_HINT[:160],
                    frequency=kri.measurement_frequency.value,
                    next_collection=date(2026, 9, 4),
                )
            )
    db.flush()
