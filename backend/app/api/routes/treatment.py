from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.acceptance import authorized
from app.api.routes.context import commit
from app.api.routes.provenance import require
from app.db.session import get_db
from app.models.risk import Control
from app.models.treatment import TreatmentControl, TreatmentMilestone, TreatmentPlan
from app.models.user import User
from app.schemas.context import ApprovalIn
from app.schemas.treatment import CompletionIn, MilestoneIn, MilestoneOut, PlanIn, PlanOut
from app.services import treatment

router=APIRouter(tags=["risk treatment"])

def load(db,ref): return require(db.scalar(select(TreatmentPlan).where(TreatmentPlan.plan_ref==ref).with_for_update()))
def out(db,row):
    data=PlanOut.model_validate(row)
    data.controls=list(db.scalars(select(Control.control_id).join(TreatmentControl).where(TreatmentControl.plan_id==row.id)))
    data.milestones=[MilestoneOut.model_validate(x) for x in treatment.milestones(db,row)]
    return data

@router.get("/treatment-plans",response_model=list[PlanOut])
def listing(db: Session=Depends(get_db)):
    return [out(db,x) for x in db.scalars(select(TreatmentPlan).order_by(TreatmentPlan.id))]

@router.get("/treatment-plans/{ref}",response_model=PlanOut)
def detail(ref: str,db: Session=Depends(get_db)):
    return out(db,load(db,ref))

@router.put("/treatment-plans/{ref}",response_model=PlanOut)
def save(ref: str,payload: PlanIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=authorized(treatment.save_plan,db,ref,payload,actor)
    commit(db)
    return out(db,row)

@router.put("/treatment-plans/{ref}/milestones/{milestone_ref}",response_model=MilestoneOut)
def milestone(ref: str,milestone_ref: str,payload: MilestoneIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=authorized(treatment.save_milestone,db,load(db,ref),milestone_ref,payload,actor)
    commit(db)
    return row

@router.post("/treatment-plans/{ref}/approve",response_model=PlanOut)
def approve(ref: str,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=load(db,ref)
    authorized(treatment.approve,db,row,payload.note,actor)
    commit(db)
    return out(db,row)

@router.post("/treatment-milestones/{milestone_id}/complete",response_model=MilestoneOut)
def complete(milestone_id: int,payload: CompletionIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=require(db.scalar(select(TreatmentMilestone).where(TreatmentMilestone.id==milestone_id).with_for_update()))
    authorized(treatment.complete_milestone,db,row,payload.evidence_ref,payload.note,actor)
    commit(db)
    return row

@router.post("/treatment-plans/{ref}/close",response_model=PlanOut)
def close(ref: str,payload: CompletionIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=load(db,ref)
    authorized(treatment.close,db,row,payload.evidence_ref,payload.note,actor)
    commit(db)
    return out(db,row)

@router.post("/treatment-plans/{ref}/cancel",response_model=PlanOut)
def cancel(ref: str,payload: ApprovalIn,db: Session=Depends(get_db),actor: User=Depends(current_user)):
    row=load(db,ref)
    authorized(treatment.cancel,db,row,payload.note,actor)
    commit(db)
    return out(db,row)
