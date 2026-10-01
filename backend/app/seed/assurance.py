"""Existing historical assurance records are not retroactively signed or verified."""

from datetime import date

from sqlalchemy import select

from app.models.assurance import AuditProgramme

PROGRAMME_HINT = "TODO AUTHOR:BENNY - agree risk-based audit coverage, frequency, methods and reporting responsibilities, considering previous audit results and significant changes."


def seed_assurance(db):
    if db.scalar(select(AuditProgramme.id).where(AuditProgramme.programme_ref == "AP-001")) is None:
        db.add(
            AuditProgramme(
                programme_ref="AP-001",
                owner="TODO AUTHOR:BENNY - assign the audit programme owner.",
                risk_basis=PROGRAMME_HINT,
                coverage=PROGRAMME_HINT,
                frequency=PROGRAMME_HINT,
                methods=PROGRAMME_HINT,
                reporting=PROGRAMME_HINT,
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 12, 31),
                review_date=date(2026, 12, 31),
                revision=1,
            )
        )
    db.flush()
