from datetime import date

from sqlalchemy import select

from app.models.obligations import Obligation
from app.models.risk import Control
from app.models.suppliers import Supplier

OBLIGATION_HINT = "TODO AUTHOR:BENNY - inspect the executed supplier security agreement, identify its version and jurisdiction, and approve the applicable requirements; no legal conclusion is supplied."


def seed_obligations(db):
    if db.scalar(select(Obligation.id).where(Obligation.obligation_ref == "OBL-001")):
        return
    control = db.scalar(select(Control).where(Control.control_id == "TP-003"))
    supplier = db.scalar(select(Supplier).where(Supplier.supplier_ref == "SUP-001"))
    if control and supplier:
        db.add(
            Obligation(
                obligation_ref="OBL-001",
                title="Supplier security agreement review",
                kind="CONTRACTUAL",
                source=OBLIGATION_HINT,
                source_version="TODO AUTHOR:BENNY - identify executed version.",
                jurisdiction="TODO AUTHOR:BENNY - confirm governing jurisdiction.",
                requirement=OBLIGATION_HINT,
                owner="TODO AUTHOR:BENNY - identify obligation owner.",
                review_date=date(2026, 9, 4),
                control_id=control.id,
                supplier_id=supplier.id,
                applicability="UNASSESSED",
            )
        )
        db.flush()
