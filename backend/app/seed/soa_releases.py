"""Preserve the legacy SoA as a source snapshot, not an invented new sign-off."""

from sqlalchemy import select

from app.models.soa_release import SoARelease
from app.services.soa_releases import capture, digest


def seed_releases(db):
    if db.scalar(select(SoARelease.id).limit(1)) is not None:
        return
    entries, warnings = capture(db)
    db.add(
        SoARelease(
            version="sample-source-1.0",
            status="DRAFT",
            entries=entries,
            entry_count=len(entries),
            content_digest=digest(entries),
            change_note="TODO AUTHOR:BENNY - confirm which exact SoA snapshot and evidence limitations management approved; legacy row metadata is not a release signature.",
            prepared_by="Sample source import",
            evidence_warnings=warnings,
            evidence_limitations_acknowledged=False,
        )
    )
    db.flush()
