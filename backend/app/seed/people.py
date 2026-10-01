from datetime import date

from sqlalchemy import select

from app.models.people import CompetenceRequirement

COMPETENCE_HINT = "TODO AUTHOR:BENNY - define role-specific skills and the observed assessment that demonstrates competence; attendance alone is insufficient."


def seed_people(db):
    if (
        db.scalar(
            select(CompetenceRequirement.id).where(
                CompetenceRequirement.requirement_ref == "COMP-001"
            )
        )
        is None
    ):
        db.add(
            CompetenceRequirement(
                requirement_ref="COMP-001",
                role="ISMS Manager",
                requirement=COMPETENCE_HINT,
                evaluation_method=COMPETENCE_HINT,
                owner="TODO AUTHOR:BENNY - confirm the accountable development owner.",
                review_date=date(2026, 9, 4),
            )
        )
        db.flush()
