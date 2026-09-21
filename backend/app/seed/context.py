"""Facts are copied from SCOPE.md; new judgments await the author."""
from datetime import date
from sqlalchemy import select
from app.models.context import ContextEntry,ScopeRevision
from app.models.risk import Risk
from app.services.context import FIELDS
from app.services.audit_trail import snapshot

CONTEXT_SAMPLE = [
    ("CTX-001","ISSUE","GENERAL","Single production region","All production infrastructure is in AWS eu-west-1; RISK-007 records regional outage exposure.","docs/SCOPE.md; RISK-007","RISK-007","TODO AUTHOR:BENNY - confirm how regional concentration shapes the ISMS context."),
    ("CTX-002","PARTY_REQUIREMENT","GENERAL","Enterprise customers","A.5.1 names enterprise customer contracts as a driver for the security policy set.","SoA A.5.1; RISK-009","RISK-009","TODO AUTHOR:BENNY - identify the applicable customer requirements and which the ISMS addresses."),
    ("CTX-003","ISSUE","CLIMATE","Climate relevance","A context relevance determination is required; no outcome is asserted in this sample.","ISO/IEC 27001:2022/Amd 1:2024, clauses 4.1 and 4.2",None,"TODO AUTHOR:BENNY - determine climate relevance and any related interested-party requirements."),
    ("CTX-004","PROCESS","GENERAL","Risk assessment and treatment","The platform records independent residual assessments, treatments and expiring acceptances.","docs/METHODOLOGY.md; docs/DECISIONS.md",None,"TODO AUTHOR:BENNY - confirm process inputs, outputs, interactions and accountable responsibility."),
]

def seed_context(db):
    for ref,kind,topic,title,statement,source,risk_ref,note in CONTEXT_SAMPLE:
        if db.scalar(select(ContextEntry.id).where(ContextEntry.context_ref==ref)) is not None:
            continue
        risk=db.scalar(select(Risk).where(Risk.risk_ref==risk_ref)) if risk_ref else None
        db.add(ContextEntry(context_ref=ref,kind=kind,topic=topic,title=title,statement=statement,source=source,
            owner="TODO AUTHOR:BENNY - assign the accountable context owner.",review_date=date(2027,1,31),
            relevance="UNASSESSED",decision_note=note,risk_id=risk.id if risk else None,status="DRAFT",revision=1))
    db.flush()
    if db.scalar(select(ScopeRevision.id).where(ScopeRevision.version=="sample-draft-1")) is None:
        rows=db.scalars(select(ContextEntry).where(ContextEntry.context_ref.in_([x[0] for x in CONTEXT_SAMPLE]))).all()
        db.add(ScopeRevision(version="sample-draft-1",statement="FinFlow: approximately 40 staff, fully remote, SaaS payments, EU and India customers; development in-house.",
            interfaces="AWS eu-west-1 hosts production; a third-party PSP handles cardholder data; Okta supports identity and GitHub source control.",
            exclusions="No owned or leased premises. TODO AUTHOR:BENNY - confirm organizational boundaries, dependencies and exclusions for this scope revision.",
            owner="TODO AUTHOR:BENNY - identify the scope owner.",review_date=date(2027,1,31),context_snapshot=[snapshot(x,FIELDS) for x in rows],status="DRAFT"))
    db.flush()
