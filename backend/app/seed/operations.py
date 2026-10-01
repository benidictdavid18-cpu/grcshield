from datetime import date

from sqlalchemy import select

from app.models.operations import RegisterRevision
from app.models.privacy import BusinessImpactAnalysis
from app.schemas.operations import BiaIn
from app.services.operations import view

OPERATIONS_HINT = "TODO AUTHOR:BENNY - review this retained sample BIA proposal and its provisional review date against actual operational evidence."


def seed_operations(db):
    row = db.scalar(select(BusinessImpactAnalysis).order_by(BusinessImpactAnalysis.bia_ref))
    if (
        row
        and db.scalar(
            select(RegisterRevision.id).where(
                RegisterRevision.kind == "BIA", RegisterRevision.record_ref == row.bia_ref
            )
        )
        is None
    ):
        previous = view(db, "BIA", row)
        content = {key: value for key, value in previous.items() if key in BiaIn.model_fields}
        db.add(
            RegisterRevision(
                kind="BIA",
                record_ref=row.bia_ref,
                revision=1,
                owner="TODO AUTHOR:BENNY - confirm the BIA reviewer.",
                review_date=date(2026, 12, 31),
                change_note=OPERATIONS_HINT,
                actor="sample.author",
                content=content,
                previous=previous,
                status="DRAFT",
            )
        )
        db.flush()
