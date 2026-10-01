"""Do not turn an evidence description into a fabricated security policy."""

from datetime import date

from sqlalchemy import select

from app.models.document import ControlledDocument, DocumentRevision
from app.models.soa import Evidence
from app.services.documents import digest

POLICY_CONTENT = "TODO AUTHOR:BENNY - provide the actual sample policy content referenced by EV-029; its approval description is not the policy itself."


def seed_documents(db):
    row = db.scalar(select(ControlledDocument).where(ControlledDocument.document_ref == "DOC-001"))
    if row is not None:
        return
    row = ControlledDocument(
        document_ref="DOC-001",
        title="Information security policy set",
        owner="Head of Legal & Compliance",
        classification="INTERNAL",
        source_kind="INTERNAL",
        distribution="TODO AUTHOR:BENNY - confirm policy recipients and publication channel.",
        review_date=date(2027, 4, 30),
    )
    db.add(row)
    db.flush()
    evidence = db.scalar(select(Evidence).where(Evidence.evidence_ref == "EV-029"))
    db.add(
        DocumentRevision(
            document_id=row.id,
            version="source-pending",
            content=POLICY_CONTENT,
            content_digest=digest(POLICY_CONTENT),
            change_note="Sample / Portfolio Assessment. EV-029 describes v3.0; the actual content has not been supplied.",
            author="TODO AUTHOR:BENNY - identify the policy author.",
            status="DRAFT",
            evidence_id=evidence.id if evidence else None,
        )
    )
    db.flush()
