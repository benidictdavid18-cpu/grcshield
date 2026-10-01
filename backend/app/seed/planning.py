"""Measurement definitions exist; new leadership commitments are not invented."""
from datetime import date

from sqlalchemy import select

from app.models.context import ContextEntry
from app.models.document import ControlledDocument, DocumentRevision
from app.models.kri import KriDefinition
from app.models.planning import ISMSPlan
from app.models.risk import Risk
from app.services.documents import digest

OBJECTIVE_HINT="TODO AUTHOR:BENNY - agree the measurable objective target, due date and committed resources; KRI thresholds alone are not leadership approval."
CHANGE_HINT="TODO AUTHOR:BENNY - assess ISMS change impacts, resources, timing, dependencies and rollback before approval."
SCALE_HINT="TODO AUTHOR:BENNY - document consistent likelihood and impact assignment guidance for the existing 1-5 scale without changing its scoring methodology."

def seed_planning(db):
    context=db.scalar(select(ContextEntry).where(ContextEntry.context_ref=="CTX-002"))
    process=db.scalar(select(ContextEntry).where(ContextEntry.context_ref=="CTX-004"))
    risk=db.scalar(select(Risk).where(Risk.risk_ref=="RISK-004"))
    kri=db.scalar(select(KriDefinition).where(KriDefinition.kri_ref=="KRI-001"))
    if db.scalar(select(ISMSPlan.id).where(ISMSPlan.plan_ref=="OBJ-001")) is None:
        db.add(ISMSPlan(plan_ref="OBJ-001",kind="OBJECTIVE",title="Privileged MFA objective proposal",owner=kri.owner_role,resources=OBJECTIVE_HINT,rationale="TODO AUTHOR:BENNY - confirm the context requirement this objective serves.",context_id=context.id,risk_id=risk.id,kri_id=kri.id,measure_definition=kri.formula_description,status="DRAFT",revision=1))
    if db.scalar(select(ISMSPlan.id).where(ISMSPlan.plan_ref=="CHG-001")) is None:
        db.add(ISMSPlan(plan_ref="CHG-001",kind="CHANGE",title="Controlled ISMS document workflow proposal",owner="TODO AUTHOR:BENNY - assign the ISMS change owner.",resources=CHANGE_HINT,rationale="Introduce maintained document revision, publication and acknowledgement records.",context_id=process.id,impact_assessment=CHANGE_HINT,rollback_plan=CHANGE_HINT,status="DRAFT",revision=1))
    if db.scalar(select(ControlledDocument.id).where(ControlledDocument.document_ref=="DOC-RISK-SCALE")) is None:
        document=ControlledDocument(document_ref="DOC-RISK-SCALE",title="Risk scale assignment guidance",owner="TODO AUTHOR:BENNY - assign the methodology guidance owner.",classification="INTERNAL",source_kind="INTERNAL",distribution="Risk assessment authors and reviewers",review_date=date(2027,1,31))
        db.add(document)
        db.flush()
        db.add(DocumentRevision(document_id=document.id,version="guidance-pending",content=SCALE_HINT,content_digest=digest(SCALE_HINT),change_note="The existing independent residual method and band thresholds remain unchanged.",author="TODO AUTHOR:BENNY - identify the guidance author.",status="DRAFT"))
    db.flush()
