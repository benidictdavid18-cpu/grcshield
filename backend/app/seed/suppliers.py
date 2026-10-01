from datetime import date

from sqlalchemy import select

from app.models.risk import Control
from app.models.suppliers import Supplier

SUPPLIER_HINT = "TODO AUTHOR:BENNY - review the actual agreement, shared responsibilities, information access, exit arrangements and supplier criticality."


def seed_suppliers(db):
    if db.scalar(select(Supplier.id).where(Supplier.supplier_ref == "SUP-001")):
        return
    control = db.scalar(select(Control).where(Control.control_id == "TP-002"))
    if control:
        db.add(
            Supplier(
                supplier_ref="SUP-001",
                name="AWS",
                service="Sample / Portfolio Assessment: production cloud hosting in eu-west-1.",
                owner="TODO AUTHOR:BENNY - confirm the accountable supplier owner.",
                criticality="UNASSESSED",
                information_access=SUPPLIER_HINT,
                agreement_terms=SUPPLIER_HINT,
                shared_responsibility=SUPPLIER_HINT,
                exit_plan=SUPPLIER_HINT,
                review_date=date(2026, 9, 4),
                control_id=control.id,
                status="DRAFT",
            )
        )
        db.flush()
