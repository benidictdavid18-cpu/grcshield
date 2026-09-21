"""A draft makes the real review/delivery date conflict visible rather than inventing agreement."""
from sqlalchemy import select
from app.models.treatment import TreatmentPlan,TreatmentControl,TreatmentMilestone
from app.models.risk import Risk,Control
from app.models.soa import RemediationItem

TREATMENT_HINT="TODO AUTHOR:BENNY - reconcile REM-001's October delivery with the September risk review; agree resources and milestones or revise the review schedule explicitly."

def seed_treatment(db):
    if db.scalar(select(TreatmentPlan.id).where(TreatmentPlan.plan_ref=="TPL-004-DRAFT")) is not None: return
    risk=db.scalar(select(Risk).where(Risk.risk_ref=="RISK-004"))
    control=db.scalar(select(Control).where(Control.control_id=="AC-002"))
    remediation=db.scalar(select(RemediationItem).where(RemediationItem.remediation_ref=="REM-001"))
    plan=TreatmentPlan(plan_ref="TPL-004-DRAFT",risk_id=risk.id,title="Privileged MFA treatment planning",owner=risk.owner_role,
        resources=TREATMENT_HINT,rationale=risk.treatment_summary,review_deadline=risk.next_review,status="DRAFT",revision=1)
    db.add(plan)
    db.flush()
    db.add(TreatmentControl(plan_id=plan.id,control_id=control.id))
    db.add(TreatmentMilestone(plan_id=plan.id,review_deadline=plan.review_deadline,milestone_ref="MILE-004-01",
        title="TODO AUTHOR:BENNY - agree delivery milestones at the next risk review.",owner=remediation.owner,due_date=risk.next_review,remediation_id=remediation.id,status="OPEN"))
    db.flush()
